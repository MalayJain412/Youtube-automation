## YouTube Automation Pipeline (MVP)

### What it does

- Reads `data/input/topics.csv` (topic + two characters)
- Generates a JSON dialogue with Azure OpenAI
- Generates per-line WAV files using Cartesia
- Builds a timeline and renders a vertical Shorts video using a random gameplay segment

### Quick start

1. Install deps: `pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and fill keys
3. Ensure gameplay videos exist in `youtube-videos-download/videos/`
4. Ensure avatar images exist in `avatars/` named as `<speaker>.png` (e.g., `aniket.png`)
5. Ensure voice IDs exist in `.env` as `VOICE_ID_<SPEAKER>` (e.g., `VOICE_ID_ANIKET`)

### CLI

- Import jobs: `python -m ytautomation.cli import --csv data/input/topics.csv`
- Run job: `python -m ytautomation.cli run --job-id 1`

### API

- Start: `python -m uvicorn ytautomation.api.main:app --reload`
- Import: `POST /jobs/import`
- Run: `POST /jobs/{job_id}/run`
