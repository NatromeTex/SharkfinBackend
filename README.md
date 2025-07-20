# SHARKFIN

A simple yet powerful local-first media streaming server that allows you to stream your personal video collection to any device on your network. Built with flexibility in mind, it offers **on-the-fly transcoding**, **seek support**, **metadata management**, and **poster/backdrop handling** — all self-hosted.

---

## ✨ Features

- 🎬 **Stream Your Movies**
  - Serve your personal movie collection over the network.
  - Watch from any device with a browser or media player.
  - Support for **original quality** and **live transcoded streams** using `ffmpeg`.

- ⚡ **On-the-Fly Transcoding with Seek Support**
  - I am particularly proud of this part of the code
  - Transcodes media using `h264_nvenc` (or other codecs as configured).
  - Supports seeking while transcoding, enabling fast-forward, rewind, and jumping to a timestamp without buffering issues.

- 📁 **Library Scan Utility**
  - Scans your media folders and catalogs the content.
  - Automatically generates JSON metadata per movie.
  - Detects and adapts to file renaming or structural changes.
  - Informs you of missing **posters** or **backdrops** for each movie.

- 🖼️ **Poster & Backdrop Management**
  - Easily serve high-quality posters and backdrops via endpoints.
  - Includes a **resize tool** to normalize all posters/backdrops to a consistent AVIF format and resolution.

- 🌐 **FastAPI Backend**
  - RESTful API endpoints to fetch metadata, stream video, and serve assets.
  - Modular and extensible design for custom endpoints or enhancements.

---

## 📂 Project Structure

```
media-server/
├── scan.py              # Scans media folders and generates metadata JSON
├── resize.py            # Resizes all posters/backdrops and converts to AVIF
├── app.py            # FastAPI app: serves endpoints and streams media
├── data/
│   ├── posters/                   # Posters folder
│   │   └── <id>.avif/             # All movie posters in .avif format
│   ├── backdrops/                 # Backdrops folder
│   │   └── <id>.avif/             # All movie backdrops in .avif format
│   ├── movie_metadata.json/       # All movie metadata
└   └── paths.json                 # Map of movie IDs to file paths

```

---

## 🚀 Endpoints

### 📜 Metadata
- `GET /data/movies` — Get all movie metadata.
- `GET /static/poster/<id>` — Get AVIF poster by movie ID.
- `GET /static/backdrop/<id>` — Get AVIF backdrop by movie ID.

### 🎥 Streaming
- `GET /movie/stream/<id>/playlist.m3u8` — Grabs the playlist containing all segments for streaming.
- `GET /movie/stream/<id>/segment-{segment_number}.ts` — Stream with **on-the-fly transcoding** (with seek support).
- `GET /movie/stream-full/<id>` — Stream at **original quality**.

---

## ⚙️ Prerequisites

- Python 3.10+
- `ffmpeg` installed with NVENC or desired codec
- Python packages:
  ```bash
  pip install -r requirements.txt
  ```

---

## 🛠️ Setup

1. **Scan your media folder**:
   ```bash
   python scan.py /path/to/your/media
   ```

2. **Resize and normalize all posters/backdrops**:
   ```bash
   python resize.py
   ```

3. **Start the server**:
   ```bash
   fastapi run app.py
   ```

3. **Start the frontend server**:
   ```bash
   cd SharkfinFrontend & npm run
   ```

4. Open your browser and enjoy at:
   ```
   http://<your-local-ip>:5173
   ```

---

## 🔄 Media Changes

The scan utility will:
- Detect file changes and auto-update metadata.
- Rename or fix inconsistencies in filenames automatically.
- Inform you of missing assets (e.g., poster/backdrop).

---

## 📱 Access From Any Device

Ensure your computer and target device are on the same Wi-Fi/network or just use tailscale. Open the streaming link on mobile, smart TV, or any browser.

---

## 📌 Roadmap (Planned Features)
- User accounts and watchlists
- Subtitle support
- Better mobile UI and remote control
- Music/TV support with smart categorization
- IP P2P support

---

## 🧑‍💻 Author

Made with ❤️ by Aditya SK
