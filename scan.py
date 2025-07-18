import os
import re
import json
import shutil
from pathlib import Path
from moviepy.editor import VideoFileClip

VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.avi', '.mov'}

TARGET_FOLDER = os.path.join('path/to','folder') #change this to your library

POSTER_BASE_URL = '/static/poster/'
BACKDROP_BASE_URL = '/static/backdrop/'
POSTER_BASE_PATH = './data/posters'
POSTER_NEXT_PATH = './data/update'
TITLE_YEAR_PATTERN = re.compile(r'^(?P<title>.+?)\s*\((?P<year>\d{4})\)')

os.makedirs(POSTER_NEXT_PATH, exist_ok=True)

def scan():
    movie_list = []
    movie_id = 1

    for root, dirs, files in os.walk(TARGET_FOLDER):
        for file in files:
            file_ext = Path(file).suffix.lower()
            if file_ext in VIDEO_EXTENSIONS:
                folder_name = Path(root).name
                match = TITLE_YEAR_PATTERN.match(folder_name)
                if match:
                    folder = match.group('title').strip()
                    year = int(match.group('year'))
                    movie_data = {
                        "id": movie_id,
                        "title": folder,
                        "folder": folder,
                        "year": year,
                        "poster_url": f"{POSTER_BASE_URL}{movie_id}.avif"
                    }
                    movie_list.append(movie_data)
                    movie_id += 1
                else:
                    print(f"Skipped: Could not parse title/year from folder: {folder_name}")

    output_path = './data/movie_metadata.json'

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(movie_list, f, indent=4)
    print(f"Done. Saved {len(movie_list)} movies to {output_path}")

def reScan():
    movie_list = []
    movie_id = 1

    old_metadata_path = './data/movie_metadata.json'
    old_titles_by_folder = {}

    if os.path.exists(old_metadata_path):
        with open(old_metadata_path, 'r', encoding='utf-8') as f:
            old_data = json.load(f)
            old_titles_by_folder = {m['folder']: m['title'] for m in old_data}

    for root, dirs, files in os.walk(TARGET_FOLDER):
        for file in files:
            file_ext = Path(file).suffix.lower()
            if file_ext in VIDEO_EXTENSIONS:
                folder_name = Path(root).name
                match = TITLE_YEAR_PATTERN.match(folder_name)
                if match:
                    folder = match.group('title').strip()
                    year = int(match.group('year'))
                    video_path = os.path.join(root, file)
                    try:
                        clip = VideoFileClip(video_path)
                        duration = int(clip.duration)
                        clip.reader.close() # type: ignore
                        if clip.audio:
                            clip.audio.reader.close_proc() # type: ignore
                    except Exception as e:
                        print(f"Error getting duration for {video_path}: {e}")
                        duration = None
                    try:
                        clip = VideoFileClip(video_path)
                        duration = int(clip.duration)
                        width, height = clip.size
                        resolution = f"{width}x{height}"

                        # Determine quality label
                        if height > 2160:
                            quality = "4K+"
                        elif height > 1440:
                            quality = "4K"
                        elif height > 1080:
                            quality = "2K"
                        elif height >= 720:
                            quality = "HD"
                        else:
                            quality = "SD"

                        clip.reader.close() # type: ignore
                        if clip.audio:
                            clip.audio.reader.close_proc() # type: ignore

                    except Exception as e:
                        print(f"Error reading video {video_path}: {e}")
                        duration = None
                        resolution = None
                        quality = "Unknown"

                    # Preserve manually edited title if it exists
                    title = old_titles_by_folder.get(folder, folder)

                    movie_data = {
                        "id": movie_id,
                        "title": title,
                        "folder": folder,
                        "year": year,
                        "poster_url": f"{POSTER_BASE_URL}{movie_id}.avif",
                        "backdrop_url": f"{BACKDROP_BASE_URL}{movie_id}.avif",
                        "duration": duration,
                        "quality": quality
                    }
                    movie_list.append(movie_data)
                    movie_id += 1
                else:
                    print(f"Skipped: Could not parse title/year from folder: {folder_name}")

    output_path = './data/movie_metadata.tmp.json'

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(movie_list, f, indent=4)
    print(f"Done. Saved {len(movie_list)} movies to {output_path}")


def trackChanges():
    old_data = []
    new_data = []
    with open('./data/movie_metadata.json', 'r') as f:
        old_json = json.load(f)
    with open('./data/movie_metadata.tmp.json', 'r') as f:
        new_json = json.load(f)

    old_data = [{"id": m["id"], "folder": m.get("folder")} for m in old_json]
    new_data = [{"id": m["id"], "folder": m.get("folder")} for m in new_json]
    
    for file in os.listdir(POSTER_BASE_PATH):
        file_id = str(file).split('.')[0]
        file_folder = next((item["folder"] for item in old_data if str(item["id"]) == file_id), None)
        new_id = next((entry['id'] for entry in new_data if entry['folder'] == file_folder), None)
        if new_id is None:
            print(f"Warning: No matching new_id found for folder '{file_folder}' (file: {file})")
            continue

        src_path = os.path.join(POSTER_BASE_PATH, file)
        dest_path = os.path.join(POSTER_NEXT_PATH, f"{new_id}.avif")

        os.rename(src_path, dest_path)
    
    os.remove('./data/movie_metadata.json')
    os.rename('./data/movie_metadata.tmp.json', './data/movie_metadata.json')

def catchMiss():
    with open('./data/movie_metadata.json', 'r') as f:
        data = json.load(f)

    ids = [m['id'] for m in data]

    with open('./data/poster.log', 'w') as f:
        for id in ids:
            path = os.path.join(POSTER_NEXT_PATH, f"{id}.avif")
            if not os.path.exists(path):
                f.write(f"Missing poster for {path} ({id})\n")

    for file in os.listdir(POSTER_NEXT_PATH):
        src_path = os.path.join(POSTER_NEXT_PATH, file)
        dest_path = os.path.join(POSTER_BASE_PATH, file)
        os.rename(src_path, dest_path)
    
    shutil.rmtree(POSTER_NEXT_PATH)

def scan_paths():
  movie_paths = {}
  movie_id = 1

  for root, dirs, files in os.walk(TARGET_FOLDER):
    for file in files:
      file_ext = Path(file).suffix.lower()
      if file_ext in VIDEO_EXTENSIONS:
        full_path = os.path.join(root, file).replace('\\', '/')
        movie_paths[str(movie_id)] = full_path
        movie_id += 1

  output_path = './data/path.json'
  with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(movie_paths, f, indent=4)
  print(f"Done. Saved {len(movie_paths)} entries to {output_path}")


if __name__ == '__main__':
    reScan()
    trackChanges()
    catchMiss()
    scan_paths()