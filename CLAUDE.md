# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a YouTube transcript extraction API built with FastAPI. It provides endpoints to extract transcripts from YouTube videos using the YouTube Transcript API, with proxy support for reliability.

## Architecture

- **FastAPI Application** (`main.py`): Single-file API server with transcript extraction endpoints
- **Docker Container**: Python 3.11-slim container running the FastAPI app on port 8000
- **Nginx Reverse Proxy**: SSL-terminated proxy serving the API at `api.videotoinfographics.com`
- **Let's Encrypt SSL**: Automated SSL certificate management via Certbot

## Key Components

### API Endpoints
- `GET /`: Health check
- `GET /health`: Health status
- `GET /proxy-status`: Check proxy configuration status
- `POST /transcript`: Extract transcript from YouTube URL
- `GET /transcript/{video_id}`: Extract transcript by video ID

### Proxy Configuration
The application uses a residential proxy service (hideip.network) to avoid YouTube rate limiting. Proxy credentials are hardcoded in `main.py:46-48`.

## Development Commands

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run the API locally
python main.py
# or
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Docker Commands
```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs api
docker-compose logs nginx

# Rebuild API container
docker-compose build api
docker-compose up -d api

# Stop all services
docker-compose down
```

### SSL Certificate Management
```bash
# Initial SSL setup (run once)
./init-ssl.sh

# Renew certificates (automatic via certbot container)
docker-compose exec certbot certbot renew

# Force certificate renewal
docker-compose run --rm certbot certbot renew --force-renewal
```

### Deployment
The application is configured for production deployment with:
- SSL termination at nginx
- Automatic HTTP to HTTPS redirect
- CORS headers configured
- Certificate auto-renewal

## File Structure

- `main.py`: FastAPI application with transcript extraction logic
- `requirements.txt`: Python dependencies
- `Dockerfile`: Container definition for the API
- `docker-compose.yml`: Multi-service orchestration
- `nginx/`: Nginx configuration files
- `certbot/`: SSL certificate storage
- `init-ssl.sh`: Initial SSL certificate setup script

## Important Notes

- Proxy credentials are hardcoded and should be moved to environment variables
- The API allows all CORS origins (`*`) - consider restricting in production
- SSL certificates auto-renew every 12 hours via the certbot container
- The application monkey-patches the requests library to use proxy for all HTTP calls