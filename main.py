from __future__ import annotations

import os
import json
from pathlib import Path
import subprocess
from dataclasses import dataclass
from typing import List, Optional, Dict

import yt_dlp
import spotipy
import requests
from mutagen.mp3 import MP3
from dotenv import load_dotenv
from rich.console import Console
from spotipy.oauth2 import SpotifyClientCredentials
from rich.progress import Progress, TaskID, SpinnerColumn
from mutagen.id3 import ID3, APIC, TIT2, TPE1, TALB, TYER


@dataclass
class Pattern:
    title: int
    artist: int
    separator: str


@dataclass
class Config:
    FFMPEG_PATH: str
    MUSIC_DIRECTORY: str
    BOOKMARK_POSITION: int
    SPOTIFY_CLIENT_ID: str
    SPOTIFY_CLIENT_SECRET: str
    CHROME_BOOKMARK_PATH: Path
    NAMING_PATTERN: Pattern


@dataclass
class Track:
    url: str
    name: str
    title: str
    artist: str


@dataclass
class TrackMetadata:
    year: str
    title: str
    album: str
    artist: str
    cover_url: str = None


class BookmarkParser:
    def __init__(self, config: Config):
        self.pattern = config.NAMING_PATTERN
        self.bookmark_path = config.CHROME_BOOKMARK_PATH
        self.bookmark_position = config.BOOKMARK_POSITION

    def get_tracks(self) -> List[Track]:
        with open(self.bookmark_path) as fp:
            bookmarks = json.load(fp)
        music_folder = bookmarks["roots"]["bookmark_bar"]["children"][self.bookmark_position]["children"]
        return [self._create_track(bookmark) for bookmark in music_folder]

    def _create_track(self, bookmark) -> Track:
        parts = bookmark["name"].split(self.pattern.separator)
        return Track(
            url=bookmark["url"],
            name=bookmark["name"],
            title=parts[self.pattern.title],
            artist=parts[self.pattern.artist],
        )


class SpotifyMetadataFetcher:
    def __init__(self, config: Config):
        self.spotify = spotipy.Spotify(
            auth_manager=SpotifyClientCredentials(
                client_id=config.SPOTIFY_CLIENT_ID,
                client_secret=config.SPOTIFY_CLIENT_SECRET,
            )
        )

    def get_metadata(self, track: Track) -> Optional[TrackMetadata]:
        results = self.spotify.search(q=f"track:{track.title} artist:{track.artist}", limit=10)
        if not results or not results["tracks"]["items"]:
            return None

        track_info = results["tracks"]["items"][0]
        return TrackMetadata(
            title=track_info["name"],
            album=track_info["album"]["name"],
            artist=track_info["artists"][0]["name"],
            year=track_info["album"]["release_date"][:4],
            cover_url=track_info["album"]["images"][0]["url"] if track_info["album"]["images"] else None
        )


class AudioDownloader:
    def __init__(self, config: Config):
        self.ffmpeg_path = config.FFMPEG_PATH
        self.music_dir = config.MUSIC_DIRECTORY
        os.makedirs(self.music_dir, exist_ok=True)

    def download(self, track: Track, task_id: TaskID, progress: Progress) -> Optional[str]:
        options = dict(
            quiet=True,
            extractaudio=True,
            format="bestaudio/best",
            ffmpeg_location=self.ffmpeg_path,
            outtmpl=f"{self.music_dir}/{track.name}.%(ext)s",
            progress_hooks=[lambda d: self._progress_hook(d, track, task_id, progress)],
        )

        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(track.url, download=False)
                file_extension = info.get("ext", "unknown")
                ydl.download([track.url])
                return file_extension
        except Exception as e:
            print(f"Error downloading '{track.name}': {e}")
            return None

    @staticmethod
    def _progress_hook(d: Dict, track: Track, task_id: TaskID, progress: Progress):
        if d["status"] == "downloading":
            downloaded = d.get("downloaded_bytes", 0)
            total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
            if total > 0:
                progress.update(task_id, completed=downloaded, total=total)
            progress.update(task_id, description=f"[green]Downloading: '{track.name}'")


class AudioConverter:
    def __init__(self, config: Config):
        self.music_dir = config.MUSIC_DIRECTORY

    def convert_to_mp3(self, track: Track, original_extension: str):
        input_file = f"{self.music_dir}/{track.name}.{original_extension}"
        output_file = f"{self.music_dir}/{track.name}.mp3"

        subprocess.run([
            "ffmpeg", "-i", input_file,
            "-vn", "-ar", "44100", "-b:a", "192k",
            "-y", output_file
        ], capture_output=True)

        os.remove(input_file)

        return output_file


class MetadataWriter:
    @staticmethod
    def write_to_disk(filepath: str, metadata: TrackMetadata):
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


class MusicProcessor:
    def __init__(self, config: Config):
        self.console = Console()
        self.metadata_writer = MetadataWriter()
        self.converter = AudioConverter(config)
        self.downloader = AudioDownloader(config)
        self.bookmark_parser = BookmarkParser(config)
        self.metadata_fetcher = SpotifyMetadataFetcher(config)

    def process_tracks(self):
        tracks = self.bookmark_parser.get_tracks()

        self.console.print(f"[blue]i[/blue] Found {len(tracks)} tracks to download\n")

        progress = Progress(SpinnerColumn(), *Progress.get_default_columns(), console=self.console)

        with progress:
            overall_task = progress.add_task(f"[cyan]Processing {len(tracks)} tracks", total=len(tracks))

            for track in tracks:
                process_task = progress.add_task(f"[green]Processing: '{track.name}'", total=100)

                # Download
                if extension := self.downloader.download(track, process_task, progress):
                    self.console.print(f"[green]✓[/green] Downloaded: '{track.name}'")

                    # Convert
                    output_file = self.converter.convert_to_mp3(track, extension)
                    self.console.print(f"[green]✓[/green] Converted to MP3")

                    # Add metadata
                    if metadata := self.metadata_fetcher.get_metadata(track):
                        self.metadata_writer.write_to_disk(output_file, metadata)
                        self.console.print(f"[green]✓[/green] Added metadata\n")
                    else:
                        self.console.print(f"[yellow]![/yellow] No metadata found\n")

                progress.update(overall_task, advance=1)
                progress.remove_task(process_task)

            progress.remove_task(overall_task)
        self.console.print("[green]✓[/green] All tracks processed!")


def main():
    load_dotenv()

    config = Config(
        SPOTIFY_CLIENT_ID=os.environ.get("SPOTIFY_CLIENT_ID") or "client-id",
        SPOTIFY_CLIENT_SECRET=os.environ.get("SPOTIFY_CLIENT_SECRET") or "client-secret",
        FFMPEG_PATH=os.environ.get("FFMPEG_PATH") or "/usr/bin/ffmpeg",
        CHROME_BOOKMARK_PATH=Path(os.environ.get("CHROME_BOOKMARK_PATH")),
        BOOKMARK_POSITION=int(os.environ.get("BOOKMARK_POSITION", 0)),
        MUSIC_DIRECTORY=os.environ.get("MUSIC_DIRECTORY") or "./downloaded_musics",
        NAMING_PATTERN=Pattern(
            title=int(os.environ.get("TITLE_POSITION", 1)),
            artist=int(os.environ.get("ARTIST_POSITION", 0)),
            separator=os.environ.get("MUSIC_SEPARATOR") or " - ",
        ),
    )

    processor = MusicProcessor(config)
    processor.process_tracks()


if __name__ == "__main__":
    main()
