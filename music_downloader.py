from __future__ import unicode_literals
import json
import os
import urllib.request
from typing import Dict, List, Any
from urllib.error import URLError
import eyed3
import mutagen.id3
import spotipy
import yt_dlp
from dotenv import load_dotenv
from mutagen.mp3 import MP3
from spotipy.oauth2 import SpotifyClientCredentials
from tqdm import tqdm


""" --- PARAMETERS ------------------------------------------------------------------------------------------ """

# Suppress non-error warnings from eyed3 library
eyed3.log.setLevel("ERROR")

# Load environment variables from .env file
load_dotenv()

# Spotify API configuration using environment variables
SPOTIFY_CLIENT_ID = os.environ["SPOTIFY_CLIENT_ID"]
SPOTIFY_CLIENT_SECRET = os.environ["SPOTIFY_CLIENT_SECRET"]
SP = spotipy.Spotify(
    auth_manager=SpotifyClientCredentials(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET
    )
)

# Options for youtube-dl, specifying audio format and post-processing settings
YOUTUBE_DL_OPTIONS = {
    "ffmpeg_location": "/usr/bin/ffmpeg",
    "format": "bestaudio/best",
    "extractaudio": True,
    "postprocessors": [{
        "key": "FFmpegExtractAudio",
        "preferredcodec": "mp3",
        "preferredquality": "192"
    }]}

# Default path for downloading music files
MUSIC_DIR = "downloaded_musics"
os.makedirs(MUSIC_DIR, exist_ok=True)

# Default path for Chrome bookmarks
PATH = os.environ["CHROME_BOOKMARK_PATH"]

""" --------------------------------------------------------------------------------------------------------- """


def levenshtein_dist_percent(str1, str2):
    """ Calculate the levenshtein distance (as a percentage) to fetch the best match from the spotify API """

    len_str1 = len(str1) + 1
    len_str2 = len(str2) + 1

    # Initialize a matrix to store distances
    matrix = [[0] * len_str2 for _ in range(len_str1)]

    # Initialize first row and column
    for i in range(len_str1):
        matrix[i][0] = i

    for j in range(len_str2):
        matrix[0][j] = j

    # Fill in matrix based on Levenshtein distance algorithm
    for i in range(1, len_str1):
        for j in range(1, len_str2):
            cost = 0 if str1[i - 1] == str2[j - 1] else 1

            # Deletion, Insertion, Substitution
            matrix[i][j] = min(matrix[i - 1][j] + 1, matrix[i][j - 1] + 1, matrix[i - 1][j - 1] + cost)

    # Calculate Levenshtein distance
    distance = matrix[-1][-1]

    # Calculate percentage
    max_len = max(len_str1 - 1, len_str2 - 1)
    distance_percentage = (1 - distance / max_len) * 100

    return distance_percentage


def retrieve_musics_from_bookmarks(position: int) -> List[Dict]:
    """ Retrieve music URLs from Chrome bookmarks and return a list of dictionaries. """

    # Expand default path
    path = os.path.expanduser(PATH)

    # Read JSON bookmark data into dict
    try:
        with open(path) as bookmark_file:
            bookmark_data = json.load(bookmark_file)
    except Exception as e:
        raise Exception(f"[ERROR] - Unable to open the bookmark file: {e}. Exiting.")

    # Extract music URLs from specified bookmark position
    try:
        music_data = bookmark_data["roots"]["bookmark_bar"]["children"][position]["children"]
    except Exception as e:
        raise Exception(f"[ERROR] - Unable to extract the music folder: {e}. Exiting.")

    return music_data


def download_cover_to_hdd(cover_name: str, cover_url: str):
    """ Download the cover image and save it to the local hard drive. """

    try:
        urllib.request.urlretrieve(cover_url, f"{cover_name}.png")
    except URLError as e:
        raise Exception(f"[ERROR] - Failed to download cover from {cover_url}: {e}")
    except Exception as e:
        raise Exception(f"An error occurred while downloading the cover: {e}")


def fetch_spotify_metadata(title: str, artist: str) -> Dict[str, Any]:
    """ Retrieve metadata for a song from the Spotify API using its title and artist. """

    # Default metadata values
    metadata = {
        "artist": artist,
        "title": title,
        "album": "Unknown",
        "year": 1900,
        "cover_url": None,
    }

    # Use Spotify API to search for song title
    search_results = SP.search(q=title, limit=10)

    if search_results:
        lev_dist_percent = []
        for track in search_results["tracks"]["items"]:
            # Calculate Levenshtein distance for each track's artist
            artiste_API = track["artists"][0]["name"].lower()
            lev_dist_percent.append(levenshtein_dist_percent(artiste_API, artist.strip().lower()))

        # Identify track with highest Levenshtein distance
        min_index = min(range(len(lev_dist_percent)), key=lambda x: lev_dist_percent[x])
        selected_track  = search_results["tracks"]["items"][min_index]

        # Extract metadata from selected track
        metadata["album"] = selected_track["album"]["name"]
        metadata["cover_url"] = selected_track["album"]["images"][0]["url"]
        metadata["year"] = selected_track["album"]["release_date"]

        # If precision is higher than 'year', extract only 'year'
        if selected_track["album"]["release_date_precision"] != "year":
            metadata["year"] = selected_track["album"]["release_date"].split("-")[0]

    return metadata


def add_metadata_to_music(music_name: str, metadata: Dict[str, Any]):
    """ Add metadata to the downloaded music file. """

    # Define paths for music file and cover image
    mp3_path = os.path.join(MUSIC_DIR, f"{music_name}.mp3")
    cover_name = f"{music_name}.png"

    try:
        # Load and initialize tags for music file
        mp3 = eyed3.load(mp3_path)
        mp3.initTag()

        # Set metadata tags
        mp3.tag.title = metadata["title"]
        mp3.tag.artist = metadata["artist"]
        mp3.tag.album_artist = metadata["artist"]
        mp3.tag.album = metadata["album"]

        # Save added tags using eyed3
        mp3.tag.save(version=eyed3.id3.ID3_V2_3)

        # Save cover image and year using mutagen
        audio = MP3(mp3_path, ID3=mutagen.id3.ID3)

        # Add cover image to tags
        cover_image  = mutagen.id3.APIC(encoding=3, mime="image/png", type=3, desc="Cover",
                                        data=open(cover_name, "rb").read())
        audio.tags.add(cover_image)

        # Add year to tags
        year_tag = mutagen.id3.TYER(encoding=3, text=str(metadata["year"]))
        audio.tags.add(year_tag)

        # Save modified tags
        audio.save(v2_version=3)

        # Remove temporarily downloaded cover image
        os.remove(cover_name)
    except Exception as e:
        raise Exception(f"An error occurred while adding metadata: {e}")


def download_music(music_url: str, music_name: str) -> bool:
    """ Download a music from the given URL and save it to the specified directory. """

    try:
        # Set output template for downloaded music file
        YOUTUBE_DL_OPTIONS["outtmpl"] = f"{MUSIC_DIR}/{music_name}.%(ext)s"

        # Download YouTube video as music using yt_dlp
        with yt_dlp.YoutubeDL(YOUTUBE_DL_OPTIONS) as ydl:
            ydl.download([music_url])

        print("\nMusic downloaded successfully.")

        return True
    except Exception as e:
        print(f"An error occurred during the download: {e}")

        return False


def main():
    print("\n=== THIS PROGRAM ONLY WORKS FOR CHROME ON WINDOWS =============================================\n")

    # Get 'music' folder bookmark position in Chrome from user
    try:
        bookmark_pos = int(input("*** Position of 'music' folder in bookmarks: "))
    except ValueError as e:
        raise ValueError(f"Invalid input. Please enter a valid integer position. Error: {e}")

    # Retrieve list of music dictionaries from bookmarks
    musics_list: List[Dict] = retrieve_musics_from_bookmarks(bookmark_pos)

    # Download all musics files
    for music_dict in tqdm(musics_list, ncols=70, desc="Downloading Music"):
        # Extract music information
        music_url = music_dict.get("url")
        music_name = music_dict.get("name")

        # Attempt to download music file
        if download_music(music_url, music_name):

            # Extract artist and title from music name following Chrome bookmark notation
            artist = music_name.split(" - ")[0]
            title = music_name.split(" - ")[1]

            # Fetch Spotify metadata
            metadata = fetch_spotify_metadata(title, artist)

            # Download cover image
            if metadata.get("cover_url"):
                download_cover_to_hdd(music_name, metadata["cover_url"])

            # Add metadata to downloaded music file
            add_metadata_to_music(music_name, metadata)

            print("Metadata added successfully.")

    print("\n=== PROCESS COMPLETED =========================================================================\n")


if __name__ == "__main__":
    main()
