import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """ Config class for environment variables """

    # Spotify information
    SPOTIFY_CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID")
    SPOTIFY_CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET")

    # Chrome bookmark and FFMPEG path
    CHROME_BOOKMARK_PATH = os.environ.get("CHROME_BOOKMARK_PATH")
    FFMPEG_LOCATION = os.environ.get("FFMPEG_LOCATION") or "/usr/bin/ffmpeg"

    # Music bookmark information
    MUSIC_DIRECTORY = os.environ.get("MUSIC_DIRECTORY") or "downloaded_musics"
    MUSIC_BOOKMARK_POSITION = int(os.environ.get("MUSIC_BOOKMARK_POSITION", 0))
    MUSIC_NAMING_CONVENTION = {
        "artist": int(os.environ.get("MUSIC_ARTIST_POSITION", 0)),
        "separation": os.environ.get("MUSIC_SEPARATION") or " - ",
        "title": int(os.environ.get("MUSIC_TITLE_POSITION", 1)),
    }
