# YVD — YouTube Video Downloader

A sleek glassmorphism YouTube video downloader built with Python and CustomTkinter.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![License](https://img.shields.io/badge/License-MIT-green)

## Features

- **Modern UI** — Glassmorphism design with rounded cards, pill buttons, and gradient accents
- **Quality Selection** — Fetch and pick from all available resolutions
- **Audio + Video Merge** — Automatically merges streams and re-encodes audio to AAC
- **One Click Download** — Paste a link, pick quality, download

## Requirements

- Python 3.10+
- [FFmpeg](https://ffmpeg.org/download.html) (required for merging video + audio above 360p)

## Setup

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/YVD.git
cd YVD

# Create a virtual environment
python -m venv .venv

# Activate it
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Install FFmpeg

**Windows (winget):**
```bash
winget install --id Gyan.FFmpeg -e
```

**Windows (manual):** Download from https://www.gyan.dev/ffmpeg/builds/ and add the `bin` folder to your PATH.

The app will also auto-detect FFmpeg from common install locations.

## Run

```bash
python yvd.py
```

## License

MIT
