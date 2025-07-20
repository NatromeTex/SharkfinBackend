import os
import json
import math
import logging
import asyncio
import subprocess
from fastapi import FastAPI, HTTPException, Request, Response
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
SEGMENT_DURATION = 8

async def get_video_duration(movie_path: str) -> float:
    """Runs ffprobe to get the total duration of the video in seconds."""
    ffprobe_cmd = [
        'ffprobe',
        '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        movie_path
    ]
    
    process = subprocess.Popen(
        ffprobe_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    stdout, stderr = process.communicate()
    
    if process.returncode != 0:
        raise HTTPException(status_code=500, detail=f"ffprobe failed: {stderr.decode()}")
        
    try:
        return float(stdout.decode().strip())
    except (ValueError, TypeError):
        raise HTTPException(status_code=500, detail="Could not parse video duration from ffprobe.")


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

    return StreamingResponse(
      stream_data(),
      media_type='video/mp4',
      headers={
        'Accept-Ranges': 'bytes',
        'Cache-Control': 'no-cache'
      }
    )

  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))
  

@app.get("/movie/stream/{id}/playlist.m3u8")
async def get_hls_playlist(id: int, request: Request):

    with open(os.path.join(DATA_DIR, 'path.json'), 'r') as f:
      data = json.load(f)
    movie_path = data.get(str(id))

    duration = await get_video_duration(movie_path)
    
    # Calculate the total number of segments
    total_segments = math.ceil(duration / SEGMENT_DURATION)
    
    # The base URL for the segment files, derived from the request
    base_url = str(request.url).replace("/playlist.m3u8", "")

    # Start building the M3U8 content
    m3u8_content = [
        "#EXTM3U",
        "#EXT-X-VERSION:3",
        f"#EXT-X-TARGETDURATION:{SEGMENT_DURATION}",
        "#EXT-X-MEDIA-SEQUENCE:0",
    ]

    # Add each segment to the playlist
    for i in range(total_segments):
        m3u8_content.append(f"#EXTINF:{SEGMENT_DURATION:.6f},")
        m3u8_content.append(f"{base_url}/segment-{i}.ts")

    # Add the end tag to signify it's a VOD (Video on Demand), not a live stream
    m3u8_content.append("#EXT-X-ENDLIST")
    
    # Join the lines and return the response
    playlist = "\n".join(m3u8_content)
    return Response(content=playlist, media_type="application/vnd.apple.mpegurl")

@app.get("/movie/stream/{id}/segment-{segment_number}.ts")
async def get_video_segment(id: int, segment_number: int):
    
    with open(os.path.join(DATA_DIR, 'path.json'), 'r') as f:
      data = json.load(f)
    movie_path = data.get(str(id))

    start_time = segment_number * SEGMENT_DURATION

    # Your ffmpeg command, modified for HLS segment generation
    ffmpeg_cmd = [
        'ffmpeg',
        '-hwaccel', 'cuda',
        '-ss', str(start_time),         # Seek to the start of the segment
        '-i', movie_path,
        '-t', str(SEGMENT_DURATION),    # Set the duration of the segment
        '-vf', 'setpts=PTS-STARTPTS',   # Resets video timestamps to start from 0
        '-af', 'asetpts=PTS-STARTPTS',  # Resets audio timestamps to start from 0
        '-output_ts_offset', str(start_time),
        '-c:v', 'h264_nvenc',
        '-preset', 'p3',
        '-rc', 'vbr',
        '-cq', '20',
        '-c:a', 'aac',
        '-f', 'mpegts',                 # Output format MUST be mpegts for HLS
        '-'                             # Output to stdout
    ]

    # Create a subprocess to run ffmpeg
    process = subprocess.Popen(
        ffmpeg_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL # Capture stderr to hide logs from console
    )

    async def stream_generator():
        # Stream the output from the ffmpeg process
        while True:
            chunk = process.stdout.read(CHUNK_SIZE) # Read in chunks
            if not chunk:
                break
            yield chunk
        
        # Wait for the process to finish and check for errors
        _, stderr_data = process.communicate()
        if process.returncode != 0:
            print(f"FFmpeg error for segment {segment_number}: {stderr_data.decode()}")

    # Stream the ffmpeg output directly to the client
    return StreamingResponse(stream_generator(), media_type="video/MP2T")
  
      
@app.get('/movie/stream-full/{id}')
def stream_full(id: int):
  with open(os.path.join(DATA_DIR, 'path.json'), 'r') as f:
    data = json.load(f)
  movie_path = data.get(str(id))
  if movie_path and os.path.exists(movie_path):
    return FileResponse(movie_path, media_type='video/mp4', filename=os.path.basename(movie_path), headers={'Accept-Ranges': 'bytes'})
  raise HTTPException(status_code=404, detail="Movie not found")




