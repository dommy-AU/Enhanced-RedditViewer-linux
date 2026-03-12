# Reddit Public Media Viewer for Linux Mint

A local Flask-based Reddit media browser for Linux Mint that focuses on **public Reddit media only**. It lets you:

- search **subreddits**
- search **users**
- open an exact subreddit or user feed
- browse **images, GIF-style clips and videos** in a media-first layout
- group **multi-media Reddit posts into a single post card** instead of splitting every file into separate posts
- move through multi-media posts with **previous / next controls** and a **media count indicator**
- choose sort modes including **Best, New, Rising, Top and Hot**
- use **Top** time filters: **Now, Today, This week, This month, This year and All time**
- request mature content with the **over 18** toggle when Reddit still allows guest access
- display **up to 200 unique media items per page**
- use an instant **page search** to filter the currently visible results
- use **Extended search** to search deeper across the current subreddit or user feed
- use **Next page** from the top or bottom of the results view
- download supported media to your PC
- download Reddit-hosted videos with sound when `ffmpeg` is available
- use the **View user** button to copy a creator’s username into the **Exact user** field
- open the current subreddit or user directly on Reddit
- show a custom samurai icon on the main page from the `static` folder

The setup launcher creates a Python virtual environment, installs the required packages, checks for `ffmpeg`, starts the app and opens the viewer in your browser. A lighter launcher can also reopen the app later once the virtual environment already exists.

---

## Files and folders in this project

- `reddit_public_media_viewer.py` — the main Flask application
- `runmefirst.sh` — first-run setup and launcher script
- `launch_app.sh` — quick launcher for later use after setup is complete
- `requirements-reddit-public-media-viewer.txt` — Python dependencies
- `static/` — folder for static assets used by the app
- `static/Icon.png` — the samurai image shown on the main page

Recommended folder layout:

```text
reddit-viewer/
├── reddit_public_media_viewer.py
├── runmefirst.sh
├── launch_app.sh
├── requirements-reddit-public-media-viewer.txt
└── static/
    └── Icon.png
```

---

## Requirements

- Linux Mint
- `python3`
- `python3-venv`
- a modern browser
- internet access

Optional but recommended:

- `ffmpeg` — required for downloading Reddit-hosted videos with audio

Python packages used by the app:

- Flask
- requests

---

## Quick start

1. Put these files and folders in the same project folder:

   - `reddit_public_media_viewer.py`
   - `runmefirst.sh`
   - `launch_app.sh`
   - `requirements-reddit-public-media-viewer.txt`
   - `static/`
   - `static/Icon.png`

2. Open a terminal in that folder.

3. Make the launchers executable:

```bash
chmod +x runmefirst.sh launch_app.sh
```

4. Run the setup launcher:

```bash
./runmefirst.sh
```

5. Your browser should open automatically at:

```text
http://127.0.0.1:65010
```

If the browser does not open, paste that address into your browser manually.

---

## Quick relaunch after setup

Once `.venv` already exists, you can reopen the app faster with:

```bash
./launch_app.sh
```

This launcher checks the health endpoint, starts the app if needed and then opens the viewer in your browser.

---

## Manual start

If you would rather start it manually instead of using the launchers:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements-reddit-public-media-viewer.txt
python3 reddit_public_media_viewer.py
```

Then open:

```text
http://127.0.0.1:65010
```

---

## How to use it

### Search subreddits
Use the **Subreddits** field to search for matching subreddit names.

### Open exact subreddit
Use **Exact subreddit** when you already know the subreddit name, for example:

```text
wallpapers
```

### Search users
Use the **Users** field to search for Reddit accounts.

### Open exact user
Use **Exact user** when you already know the username, for example:

```text
spez
```

### Sort options
You can choose:

- Best
- New
- Rising
- Top
- Hot

When **Top** is selected, an extra dropdown appears for:

- Now
- Today
- This week
- This month
- This year
- All time

### Mature content toggle
Tick the mature content checkbox if you want the app to request 18+ content. This does **not** bypass Reddit restrictions. It only helps where Reddit still permits guest access to mature content.

### Page search and Extended search
Inside an open subreddit or user feed:

- type in the search field to **filter the current page instantly**
- click **Extended search** to search deeper across the current subreddit or user feed
- use **Clear extended** to return to normal browsing

Extended search is broader than the on-page filter and can scan multiple Reddit API pages. If the scan limit is reached, the app shows a notice so you know the search was cut short rather than silently failing.

### Grouped multi-media posts
If a Reddit post contains more than one media file, the viewer keeps it together as **one post card**.

That makes it easier to browse galleries and multi-file posts without seeing the same Reddit post repeated several times.

### Pagination
The app can display **up to 200 unique media items per page**.

If more results are available, use the **Next page** button at the top or bottom of the results view.

### Download media
Each post card can include a **Download** button.

- images download directly
- standard videos download directly
- Reddit-hosted DASH videos can be merged with audio during download if `ffmpeg` is installed

### View user button
Each post card can include a **View user** button.

When clicked, it places that creator’s username into the **Exact user** field so you can open their profile feed quickly.

### Open on Reddit
Each open subreddit or user view also includes an **Open on Reddit** button so you can jump to the original Reddit page in your browser.

### Main page image
The main page uses:

```text
/static/Icon.png
```

If that file is missing, renamed or placed in the wrong folder, the samurai image on the home page will not display correctly.

---

## What the app does well

- clean media-first layout
- no comments section
- subreddit and user search
- exact subreddit and exact user browsing
- on-page results filtering
- broader Extended search inside the current subreddit or user feed
- grouped handling for multi-media Reddit posts
- unique media filtering to reduce duplicates
- supports direct images, preview images, Reddit-hosted videos and GIF-style clips
- videos and GIF-style clips are lazy-loaded to keep the page more responsive
- supports direct file downloads
- supports Reddit video downloads with audio when `ffmpeg` is installed
- includes a custom hero image from the `static` folder
- exposes a simple local health endpoint

---

## Limits and behaviour

This viewer is designed for **public Reddit content available to guest access**.

It does **not**:

- log into Reddit
- bypass private subreddits
- bypass quarantined or removed communities
- bypass regional guest-access restrictions
- bypass Reddit rate limits

If Reddit blocks access, the app will return an error message in the page.

---

## Troubleshooting

### `python3 is not installed`
Install Python 3 first.

```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip
```

### `reddit_public_media_viewer.py not found`
Make sure the main Python file is in the same folder as `runmefirst.sh`.

### `requirements-reddit-public-media-viewer.txt not found`
Make sure the requirements file is in the same folder as `runmefirst.sh`.

### `static/Icon.png` does not appear
Check that:

- the folder is named exactly `static`
- the file is named exactly `Icon.png`
- the folder sits beside `reddit_public_media_viewer.py`
- the image file is a valid PNG

Correct structure:

```text
reddit-viewer/
├── reddit_public_media_viewer.py
└── static/
    └── Icon.png
```

### Browser does not open automatically
Open this manually:

```text
http://127.0.0.1:65010
```

### Port already in use
Another app may already be using port `65010`.
Stop the existing process or edit the port inside `reddit_public_media_viewer.py`.

### Rate limited by Reddit
Wait a little and try again.

### Extended search finds fewer results than Reddit’s website
That can happen because this app uses guest-accessible Reddit endpoints, search limits and media-only filtering.

Try:

- narrowing the search term
- changing the sort mode
- using a different Top time range if relevant
- going to the next page of results

### Some content does not load
That usually means one of these:

- Reddit does not allow guest access for that content
- the subreddit or user no longer exists
- the content is private, quarantined or removed
- Reddit is temporarily rate limiting requests

### Downloaded Reddit video has no sound
Reddit often separates video and audio streams. For merged downloads with sound:

- make sure `ffmpeg` is installed
- use the **Download** button for a Reddit-hosted video
- ensure the launcher detects `ffmpeg`

You can verify `ffmpeg` with:

```bash
ffmpeg -version
```

### `ffmpeg` is not installed
Install it with:

```bash
sudo apt update
sudo apt install ffmpeg
```

### Performance feels slow on pages with lots of motion media
This app already lazy-loads videos and GIF-style clips, but very media-heavy pages can still be demanding depending on your browser and hardware.

---

## Useful commands

### Stop the app
In the terminal where it is running, press:

```bash
Ctrl+C
```

### Remove the virtual environment
If you want a clean reinstall:

```bash
rm -rf .venv
```

### Reinstall dependencies

```bash
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements-reddit-public-media-viewer.txt
```

### Check that ffmpeg is installed

```bash
ffmpeg -version
```

### Check that the app is running

```bash
curl -fsS http://127.0.0.1:65010/healthz
```

---

## Health check

The app also exposes a simple health endpoint:

```text
http://127.0.0.1:65010/healthz
```

Expected response:

```json
{"status": "ok"}
```

---

## Notes

This is a **local desktop viewer** for Linux Mint using Flask and requests. It is best suited for quick browsing of public Reddit media without needing a heavy desktop client.

The samurai hero image is loaded from the local `static` folder, so keep that folder with the project when moving or backing up the app.

If you later want, this README can also be expanded with:

- screenshots
- packaging instructions
- known issues
- changelog
