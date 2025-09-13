from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
from youtube_transcript_api.proxies import WebshareProxyConfig
import requests
import json
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

class InfographicRequest(BaseModel):
    video_url: str
    languages: Optional[List[str]] = ["en"]
    num_points: Optional[int] = 5

class InfographicResponse(BaseModel):
    video_id: str
    infographic_points: List[str]
    language: str
    proxy_status: str
    num_points: int

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

def clean_transcript_text(text: str) -> str:
    """Clean transcript text by removing newlines and extra whitespace"""
    if not text:
        return text

    # Replace newlines with spaces
    cleaned = text.replace('\n', ' ')

    # Replace multiple spaces with single spaces
    cleaned = ' '.join(cleaned.split())

    return cleaned

def generate_infographic_summary(transcript_text: str, num_points: int = 5) -> List[str]:
    """Generate infographic points from transcript using Google Gemini 1.5"""
    OPENROUTER_API_KEY = "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"

    # Validate num_points
    if num_points < 1 or num_points > 10:
        num_points = 5

    # Truncate text if too long (keep within token limits)
    if len(transcript_text) > 8000:
        transcript_text = transcript_text[:8000] + "..."

    prompt = f"""You are an expert content summarizer. Analyze this YouTube video transcript and create exactly {num_points} high-quality summary points that capture the most important and actionable information.

REQUIREMENTS for each point:
• Be a complete, standalone statement (not dependent on other points)
• Focus on key insights, main ideas, facts, or actionable takeaways
• Use clear, engaging, and professional language
• Maximum 25 words per point
• Avoid repetition between points
• Make it informative and valuable to readers

FORMAT: Return exactly {num_points} points, each on a separate line, numbered 1-{num_points}.

TRANSCRIPT:
{transcript_text}

SUMMARY POINTS:"""

    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://api.videotoinfographics.com",
                "X-Title": "YouTube Infographics API"
            },
            data=json.dumps({
                "model": "google/gemini-flash-1.5",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 200,
                "temperature": 0.3
            }),
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            content = result["choices"][0]["message"]["content"]

            # Parse the numbered points from the response
            lines = content.strip().split('\n')
            points = []

            for line in lines:
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith('•') or line.startswith('-')):
                    # Remove numbering and clean up
                    cleaned_point = re.sub(r'^[\d\.\)\-\•\*\s]+', '', line).strip()
                    if cleaned_point:
                        points.append(cleaned_point)

            # Ensure we have exactly the requested number of points
            if len(points) >= num_points:
                return points[:num_points]
            elif len(points) > 0:
                # If we have fewer than requested, pad with the content
                while len(points) < num_points and len(points) < len(lines):
                    for line in lines:
                        line = line.strip()
                        if line and line not in points:
                            points.append(line)
                            if len(points) >= num_points:
                                break
                return points[:num_points]
            else:
                # Fallback: split content into sentences
                sentences = [s.strip() for s in content.split('.') if s.strip()]
                return sentences[:num_points] if len(sentences) >= num_points else sentences
        else:
            raise Exception(f"OpenRouter API error: {response.status_code}")

    except Exception as e:
        # Fallback: create simple points from transcript
        sentences = [s.strip() for s in transcript_text.split('.') if s.strip() and len(s.strip()) > 20]
        fallback_points = []

        # Create fallback points based on requested number
        for i in range(num_points):
            if i < len(sentences):
                fallback_points.append(f"Key point {i+1}: {sentences[i][:50]}...")
            else:
                fallback_points.append(f"Video provides valuable insights and information (point {i+1})")

        return fallback_points[:num_points]

def get_youtube_transcript_api():
    """Initialize YouTube Transcript API with proxy configuration"""
    PROXY_USERNAME = "labvizce99-21"
    PROXY_PASSWORD = "x2za3x15c9ah"

    try:
        ytt_api = YouTubeTranscriptApi(
            proxy_config=WebshareProxyConfig(
                proxy_username=PROXY_USERNAME,
                proxy_password=PROXY_PASSWORD,
                filter_ip_locations=["de", "us"]
            )
        )
        proxy_status = "✅ Proxy configured: WebShare"
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

        transcript_list = ytt_api.fetch(video_id, languages=request.languages)

        formatter = TextFormatter()
        transcript_text = formatter.format_transcript(transcript_list)

        # Clean the transcript text
        cleaned_transcript = clean_transcript_text(transcript_text)

        detected_language = request.languages[0] if request.languages else "en"

        return TranscriptResponse(
            video_id=video_id,
            transcript=cleaned_transcript,
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

        transcript_list = ytt_api.fetch(video_id, languages=language_list)

        formatter = TextFormatter()
        transcript_text = formatter.format_transcript(transcript_list)

        # Clean the transcript text
        cleaned_transcript = clean_transcript_text(transcript_text)

        return TranscriptResponse(
            video_id=video_id,
            transcript=cleaned_transcript,
            language=language_list[0],
            proxy_status=proxy_status
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get transcript: {str(e)}")

@app.post("/infographic", response_model=InfographicResponse)
async def generate_infographic(request: InfographicRequest):
    """Generate configurable number of summary points from a YouTube video transcript"""
    try:
        # Validate num_points
        num_points = request.num_points or 5
        if num_points < 1 or num_points > 10:
            raise HTTPException(status_code=400, detail="num_points must be between 1 and 10")

        video_id = extract_video_id(request.video_url)
        ytt_api, proxy_status = get_youtube_transcript_api()

        # Get transcript
        transcript_list = ytt_api.fetch(video_id, languages=request.languages)

        formatter = TextFormatter()
        transcript_text = formatter.format_transcript(transcript_list)

        # Clean the transcript text
        cleaned_transcript = clean_transcript_text(transcript_text)

        # Generate infographic points using Gemini 1.5
        infographic_points = generate_infographic_summary(cleaned_transcript, num_points)

        detected_language = request.languages[0] if request.languages else "en"

        return InfographicResponse(
            video_id=video_id,
            infographic_points=infographic_points,
            language=detected_language,
            proxy_status=proxy_status,
            num_points=len(infographic_points)
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate infographic: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)