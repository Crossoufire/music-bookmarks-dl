import os

from dotenv import load_dotenv


load_dotenv()


class Config:
    # Spotify credentials
    SPOTIFY_CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID") or "client-id"
    SPOTIFY_CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET") or "client-secret"

    # FFMPEG path
    FFMPEG_PATH = os.environ.get("FFMPEG_PATH") or "/usr/bin/ffmpeg"

    # Chrome bookmarks
    CHROME_BOOKMARK_PATH = os.environ.get("CHROME_BOOKMARK_PATH")
    BOOKMARK_POSITION = int(os.environ.get("BOOKMARK_POSITION", 0))

    # Music directory
    MUSIC_DIRECTORY = os.environ.get("MUSIC_DIRECTORY") or "downloaded_musics"

    # Naming Pattern
    NAMING_PATTERN = dict(
        title=int(os.environ.get("TITLE_POSITION", 1)),
        artist=int(os.environ.get("ARTIST_POSITION", 0)),
        separator=os.environ.get("MUSIC_SEPARATOR") or " - ",
    )
