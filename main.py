from __future__ import annotations

import re
import os
import json
import subprocess
from dataclasses import dataclass
from typing import List, Optional, Dict, TypedDict

import yt_dlp
import spotipy
import requests
from mutagen.mp3 import MP3
from rich.console import Console
from spotipy.oauth2 import SpotifyClientCredentials
from rich.progress import Progress, TaskID, SpinnerColumn
from mutagen.id3 import ID3, APIC, TIT2, TPE1, TALB, TYER

from config import Config


# Initialize Rich console
console = Console()


class ChromeBookmark(TypedDict):
    url: str
    name: str


class Pattern(TypedDict):
    artist: int
    title: int
    separator: str


@dataclass
class Track:
    url: str
    name: str
    title: str
    artist: str

    @classmethod
    def from_chrome_bookmark(cls, bookmark: ChromeBookmark, pattern: Pattern) -> Track:
        parts = bookmark["name"].split(pattern["separator"])
        return cls(
            url=bookmark["url"],
            name=bookmark["name"],
            title=parts[pattern["title"]],
            artist=parts[pattern["artist"]],
        )


@dataclass
class TrackMetadata:
    year: str
    title: str
    album: str
    artist: str
    cover_url: str = None


class MusicDownloader:
    def __init__(self, config: Config):
        self.config = config
        self.spotify = spotipy.Spotify(
            auth_manager=SpotifyClientCredentials(
                client_id=config.SPOTIFY_CLIENT_ID,
                client_secret=config.SPOTIFY_CLIENT_SECRET,
            )
        )

        # Ensure music directory exists
        os.makedirs(config.MUSIC_DIRECTORY, exist_ok=True)

        # Setup yt-dlp
        self.yt_options = dict(
            quiet=True,
            extractaudio=True,
            format="bestaudio/best",
            ffmpeg_location=config.FFMPEG_PATH,
        )

    def get_bookmarked_tracks(self) -> List[Track]:
        with open(self.config.CHROME_BOOKMARK_PATH) as fp:
            bookmarks = json.load(fp)

        music_folder = bookmarks["roots"]["bookmark_bar"]["children"][self.config.BOOKMARK_POSITION]["children"]

        return [Track.from_chrome_bookmark(bm, self.config.NAMING_PATTERN) for bm in music_folder]

    def get_spotify_metadata(self, track: Track) -> Optional[TrackMetadata]:
        results = self.spotify.search(q=f"track {track.title} artist {track.artist}", limit=10)
        if not results or not results["tracks"]["items"]:
            return None

        track_info = results["tracks"]["items"][0]
        return TrackMetadata(
            title=track_info["name"],
            album=track_info["album"]["name"],
            artist=track_info["artists"][0]["name"],
            year=track_info["album"]["release_date"][:4],
            cover_url=track_info["album"]["images"][0]["url"] if track_info["album"]["images"] else None,
        )

    def download_track(self, track: Track, task_id: TaskID, progress: Progress) -> bool:
        def progress_hook(yt_dlp: Dict):
            if yt_dlp["status"] == "downloading":
                downloaded = yt_dlp.get("downloaded_bytes", 0)
                total = yt_dlp.get("total_bytes") or yt_dlp.get("total_bytes_estimate", 0)

                if total > 0:
                    progress.update(task_id, completed=downloaded, total=total)
                progress.update(task_id, description=f"[green]Downloading: '{track.name}'")

        self.yt_options["outtmpl"] = f"{self.config.MUSIC_DIRECTORY}/{track.name}.%(ext)s"
        self.yt_options["progress_hooks"] = [progress_hook]

        try:
            with yt_dlp.YoutubeDL(self.yt_options) as ydl:
                ydl.download([track.url])
            return True
        except Exception as e:
            console.print(f"[red]Error downloading '{track.name}': {e}")
            return False

    def convert_to_mp3(self, track: Track, task_id: TaskID, progress: Progress):
        input_file = f"{self.config.MUSIC_DIRECTORY}/{track.name}.webm"
        output_file = f"{self.config.MUSIC_DIRECTORY}/{track.name}.mp3"

        # Get duration for progress tracking
        probe_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                     "default=noprint_wrappers=1:nokey=1", input_file]
        duration = float(subprocess.check_output(probe_cmd).decode())
        progress.update(task_id, description=f"[green]Converting: '{track.name}'", total=duration)

        cmd = ["ffmpeg", "-i", input_file, "-vn", "-ar", "44100", "-b:a", "192k", "-progress", "pipe:1", "-y", output_file]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

        for line in process.stdout:
            if match := re.search(r"out_time_us=(\d+)", line):
                progress.update(task_id, completed=int(match.group(1)) / 1000000)

        process.wait()
        os.remove(input_file)

    def add_metadata(self, track_name: str, metadata: TrackMetadata):
        filepath = f"{self.config.MUSIC_DIRECTORY}/{track_name}.mp3"

        audio = MP3(filepath, ID3=ID3)
        if not audio.tags:
            audio.add_tags()

        audio.tags.add(TIT2(encoding=3, text=metadata.title))
        audio.tags.add(TPE1(encoding=3, text=metadata.artist))
        audio.tags.add(TALB(encoding=3, text=metadata.album))
        audio.tags.add(TYER(encoding=3, text=metadata.year))

        if metadata.cover_url:
            cover_data = requests.get(metadata.cover_url).content
            audio.tags.add(APIC(encoding=3, mime="image/png", type=3, desc="Cover", data=cover_data))

        audio.save()


def main():
    console.print("[blue]i[/blue] This script will download music from your bookmarks.")
    console.print("[blue]i[/blue] This script only works with Chrome bookmarks on Windows.")

    downloader = MusicDownloader(Config())
    tracks = downloader.get_bookmarked_tracks()

    console.print("[blue]i[/blue] Retrieving music from bookmarks...")
    console.print(f"[blue]i[/blue] Found {len(tracks)} tracks to download\n")

    # Setup progress bars
    progress = Progress(
        SpinnerColumn(),
        *Progress.get_default_columns(),
        console=console,
    )

    with progress:
        overall_task = progress.add_task(f"[cyan]Processing {len(tracks)} tracks", total=len(tracks))

        for track in tracks:
            process_task = progress.add_task(f"[green]Processing: '{track.name}'", total=100)

            if downloader.download_track(track, process_task, progress):
                console.print(f"[green]✓[/green] Successfully downloaded: '{track.name}'")
                downloader.convert_to_mp3(track, process_task, progress)
                console.print(f"[green]✓[/green] Successfully converted")
                if metadata := downloader.get_spotify_metadata(track):
                    downloader.add_metadata(track.name, metadata)
                    console.print(f"[green]✓[/green] Successfully added metadata\n")
                else:
                    console.print(f"[yellow]![/yellow] No Spotify metadata found\n")

            progress.update(overall_task, advance=1)
            progress.remove_task(process_task)

        progress.remove_task(overall_task)
    console.print("[green]✓[/green] All tracks processed!")


if __name__ == "__main__":
    main()
