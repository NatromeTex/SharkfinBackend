import os
import sys
import json
import asyncio
import logging
import subprocess
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
logger = logging.getLogger("uvicorn.error")

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    ""
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

POSTER_DIR = ".\\data\\posters"
BACKDROP_DIR = ".\\data\\backdrops"
DATA_DIR = '.\\data'
MOVIE_DIR = "E:\\media\\movies"
CHUNK_SIZE = 65536

@app.get('/')
async def root():
  return {'message':'Hello World'}

@app.get('/static/poster/{id}.avif')
def get_poster(id: int):
  path = os.path.join(POSTER_DIR, f'{id}.avif')
  if os.path.exists(path):
    return FileResponse(path, media_type='image/avif', status_code=200)
  return HTTPException(status_code=404, detail="Poster Not Found")

@app.get('/static/backdrop/{id}.avif')
def get_backdrop(id: int):
  path = os.path.join(BACKDROP_DIR, f'{id}.avif')
  if os.path.exists(path):
    return FileResponse(path, media_type='image/avif', status_code=200)
  return HTTPException(status_code=404, detail="Poster Not Found")

@app.get('/data/movies')
def get_movies():
  path = os.path.join(DATA_DIR, 'movie_metadata.json')
  if os.path.exists(path):
    with open(path, 'r') as f:
      data = json.load(f)
      return JSONResponse(data)
  return HTTPException(status_code=404, detail="Movie data not found")

@app.get('/movie/stream/{id}')
def stream_transcoded(id: int):
  # Load path.json and get path for id
  with open(os.path.join(DATA_DIR, 'path.json'), 'r') as f:
    data = json.load(f)
  movie_path = data.get(str(id))
  if not movie_path or not os.path.exists(movie_path):
    raise HTTPException(status_code=404, detail="Movie not found")

  # FFmpeg command with NVENC (no -tune)
  ffmpeg_cmd = [
    'ffmpeg',
    '-hwaccel', 'cuda',
    '-i', movie_path,
    '-c:v', 'h264_nvenc',
    '-preset', 'p3',
    '-rc', 'vbr',
    '-cq', '20',
    '-c:a', 'aac',
    '-movflags', 'frag_keyframe+empty_moov',
    '-f', 'mp4',
    '-'
  ]

  # Launch FFmpeg process
  process = subprocess.Popen(
    ffmpeg_cmd,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
  )

  if process.stdout is None:
    raise HTTPException(status_code=500, detail="FFmpeg failed to start")

  try:
    # Peek ahead to detect startup failure
    first_chunk = process.stdout.read(4096)
    if not first_chunk:
      err = process.stderr.read().decode()
      raise HTTPException(status_code=500, detail=f"FFmpeg failed to start:\n{err}")

    # Generator: send first chunk + stream the rest
    def stream_data():
      yield first_chunk
      for chunk in iter(lambda: process.stdout.read(4096), b''):
        yield chunk
      if process.stderr:
        err = process.stderr.read().decode()
        if err:
          print(f"[ffmpeg stderr for id={id}]:\n{err}")
    
    def get_duration(id: int):
      with open(os.path.join(DATA_DIR, 'MOVIE_METADATA.json'), 'r') as f:
        data = json.load(f)
      movie = next((m for m in data if m["id"] == id), None)
      if movie:
        duration = movie["duration"]
        return str(duration)
      else:
        return None
      
    print(get_duration(id))
    return StreamingResponse(
      stream_data(),
      media_type='video/mp4',
      headers={
        'Accept-Ranges': 'bytes',
        'Cache-Control': 'no-cache',
        'X-Video-duration': get_duration(id) or ""
      }
    )

  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))
  
      
@app.get('/movie/stream-full/{id}')
def stream_full(id: int):
  with open(os.path.join(DATA_DIR, 'path.json'), 'r') as f:
    data = json.load(f)
  movie_path = data.get(str(id))
  if movie_path and os.path.exists(movie_path):
    return FileResponse(movie_path, media_type='video/mp4', filename=os.path.basename(movie_path), headers={'Accept-Ranges': 'bytes'})
  raise HTTPException(status_code=404, detail="Movie not found")




