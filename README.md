# Music Downloader

Music Downloader is a Python script that allows you to download music from Chrome bookmarks and automatically add
metadata to the downloaded music files using the Spotify API.

## Features

- Downloads music from Chrome bookmarks.
- Retrieves metadata for downloaded music from the Spotify API.
- Adds metadata including title, artist, album, year, and cover image to downloaded music files.
- Supports customization of music naming convention extraction method.

## Notes

- This program is designed to work with Chrome bookmarks on Windows.
- It requires a Spotify API key (free) for the metadata.

## Prerequisites

Before you begin, ensure you have met the following requirements:

- Poetry
- Python 3.10+
- `ffmpeg` installed and added to the system `path`
- Spotify API credentials (`client-ID` and `client-secret`)

## Installation

1. Clone the repository and install dependencies

```bash
git clone https://github.com/Crossoufire/music-bookmarks-dl.git
cd music-bookmarks-dl
poetry install
```

2. Set up your environment variables by creating a `.env` file in the root directory

```
SPOTIFY_CLIENT_ID=<your_spotify_client_id>
SPOTIFY_CLIENT_SECRET=<your_spotify_client_secret>

FFMPEG_PATH=<your_ffmpeg_location> (default: "/usr/bin/ffmpeg")
CHROME_BOOKMARK_PATH=<'/mnt/c/Users/<YOUR-USERNAME>/AppData/Local/Google/Chrome/User Data/Default/Bookmarks'>
BOOKMARK_POSITION=<position_in_bookmark> (default: 0)

MUSIC_DIRECTORY=<path_to_your_music_directory> (default: "downloaded_musics")

MUSIC_SEPARATOR=<separator_token_in_the_bookmark> (default: " - ")
ARTIST_POSITION=<artist_position_after_splitting> (default: 0)
TITLE_POSITION=<title_position_after_splitting> (default: 1)
```

3. Customize the `config.py` file according to your preferences

4. Run the script

```
poetry run python main.py
```

## Examples

- If your files are named `artist - title` (e.g., `Sum 41 - In Too Deep`), the configuration would be

```
MUSIC_SEPARATOR=" - "
ARTIST_POSITION=0
TITLE_POSITION=1
```

- If your files are named `title ; artist` (e.g., `Shadow of the Day ; Linkin Park`), the configuration would be

```
MUSIC_SEPARATOR=" ; "
ARTIST_POSITION=1
TITLE_POSITION=0
```

## Usage

- Ensure your Chrome bookmarks contain a folder with music URLs following the correct pattern (ex: 'artist - title')
- Run the script, and it will download the music files, retrieve metadata, and add it to the files automatically.
