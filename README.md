# YouTube Chrome Bookmarks Music Downloader
This Python script downloads music files from your Chrome bookmarks, fetches metadata from Spotify, 
and adds the metadata to the downloaded music files.


## Features
- Take YouTube urls from a Chrome bookmark folder
- Download the musics using `yt_dlp` (fork of `youtube-dl`)
- Convert them in mp3 using the `ffmpeg` program
- Edit metadata using `eyed3` and `mutagen`
- Add new metadata using Spotify API with the `spotipy` module


## Notes
- The script assumes a specific naming convention for music files in Chrome bookmarks in the form: `artist - title` (e.g., Daft Punk - Around the world)
- Make sure to have proper permissions to read the Chrome bookmarks file.
- This script is specifically designed for `Chrome` on `Windows` (as far as I created it and used it).


## Prerequisites
Before running the script, ensure you have the following:

- Python 3.6+ installed
- Install required Python packages using the following command:

```bash
pip install -r requirements.txt
```

#### FFMPEG Installation
- Using WSL2 (meaning that your python script will also run through WSL2):
```bash
sudo apt install ffmpeg
```

- Without WSL2: Download FFMPEG and set its path in the Python script:
```env
YOUTUBE_DL_OPTIONS["ffmpeg_location"]
``` 


## Configuration
Create a .env file with the following:

```env
SPOTIFY_CLIENT_ID=your_client_id
SPOTIFY_CLIENT_SECRET=your_client_secret
CHROME_BOOKMARK_PATH=/path/to/your/chrome/bookmarks.json
```


## Usage
- Run the script using:
```bash
python music_downloader.py
```
- Enter the position of your 'music' folder in your Chrome bookmarks when prompted.
- The script will download music files, fetch metadata from Spotify, and add the metadata to the downloaded files.
