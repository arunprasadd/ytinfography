from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
import requests
import re
from typing import Optional, List

app = FastAPI(title="YouTube Transcript API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TranscriptRequest(BaseModel):
    video_url: str
    languages: Optional[List[str]] = ["en"]

class TranscriptResponse(BaseModel):
    video_id: str
    transcript: str
    language: str
    proxy_status: str

def extract_video_id(url: str) -> str:
    """Extract video ID from YouTube URL"""
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)',
        r'youtube\.com\/.*v=([^&\n?#]+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    raise ValueError("Invalid YouTube URL")

def get_youtube_transcript_api():
    """Initialize YouTube Transcript API with proxy configuration"""
    PROXY_USERNAME = "labvizce-51"
    PROXY_PASSWORD = "x2za3x15c9ah"
    PROXY_ENDPOINT = "p.webshare.io:80"

    try:
        # Configure proxy for requests session
        proxies = {
            "http": "http://labvizce-51:x2za3x15c9ah@p.webshare.io:80/",
            "https": "http://labvizce-51:x2za3x15c9ah@p.webshare.io:80/"
        }

        # Monkey patch requests to use proxy
        original_get = requests.get
        original_post = requests.post

        def proxied_get(*args, **kwargs):
            kwargs.setdefault('proxies', proxies)
            return original_get(*args, **kwargs)

        def proxied_post(*args, **kwargs):
            kwargs.setdefault('proxies', proxies)
            return original_post(*args, **kwargs)

        requests.get = proxied_get
        requests.post = proxied_post

        ytt_api = YouTubeTranscriptApi()
        proxy_status = f"✅ Proxy configured: p.webshare.io:80"
        return ytt_api, proxy_status
    except Exception as e:
        ytt_api = YouTubeTranscriptApi()
        proxy_status = f"❌ Proxy failed: {e}"
        return ytt_api, proxy_status

@app.get("/")
async def root():
    return {"message": "YouTube Transcript API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/proxy-status")
async def proxy_status():
    """Check if proxy is working"""
    _, proxy_status = get_youtube_transcript_api()
    return {"proxy_status": proxy_status}

@app.post("/transcript", response_model=TranscriptResponse)
async def get_transcript(request: TranscriptRequest):
    """Get transcript for a YouTube video"""
    try:
        video_id = extract_video_id(request.video_url)
        ytt_api, proxy_status = get_youtube_transcript_api()

        transcript_list = ytt_api.get_transcript(video_id, languages=request.languages)

        formatter = TextFormatter()
        transcript_text = formatter.format_transcript(transcript_list)

        detected_language = request.languages[0] if request.languages else "en"

        return TranscriptResponse(
            video_id=video_id,
            transcript=transcript_text,
            language=detected_language,
            proxy_status=proxy_status
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get transcript: {str(e)}")

@app.get("/transcript/{video_id}")
async def get_transcript_by_id(video_id: str, languages: Optional[str] = "en"):
    """Get transcript by video ID directly"""
    try:
        language_list = languages.split(",") if languages else ["en"]
        ytt_api, proxy_status = get_youtube_transcript_api()

        transcript_list = ytt_api.get_transcript(video_id, languages=language_list)

        formatter = TextFormatter()
        transcript_text = formatter.format_transcript(transcript_list)

        return TranscriptResponse(
            video_id=video_id,
            transcript=transcript_text,
            language=language_list[0],
            proxy_status=proxy_status
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get transcript: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)