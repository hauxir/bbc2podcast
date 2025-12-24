"""FastAPI app serving podcast RSS feed and audio files."""

import json
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, Response
from feedgen.feed import FeedGenerator

from bbc2podcast.config import AUDIO_DIR, DATA_DIR, EPISODES_FILE, get_programme_info

app = FastAPI()


def load_episodes() -> list[dict]:
    """Load episode metadata from JSON file, deduplicating by ID."""
    if not EPISODES_FILE.exists():
        return []
    with open(EPISODES_FILE) as f:
        episodes = json.load(f)
    # Deduplicate by ID, keeping the first occurrence
    seen: set[str] = set()
    unique: list[dict] = []
    for ep in episodes:
        if ep["id"] not in seen:
            seen.add(ep["id"])
            unique.append(ep)
    return unique


def generate_feed(base_url: str) -> str:
    """Generate podcast RSS feed XML."""
    episodes = load_episodes()
    info = get_programme_info()

    fg = FeedGenerator()
    fg.load_extension("podcast")
    podcast: Any = getattr(fg, "podcast")

    fg.id(f"{base_url}/feed.xml")
    fg.title(info.title)
    fg.description(info.description)
    fg.link(href=base_url, rel="alternate")
    fg.link(href=f"{base_url}/feed.xml", rel="self")
    fg.language("en")
    podcast.itunes_category("Music")
    podcast.itunes_author("BBC")
    podcast.itunes_explicit("no")
    if info.image_url:
        podcast.itunes_image(info.image_url)

    for ep in episodes:
        fe = fg.add_entry()
        fe.id(ep["id"])
        fe.title(ep["title"])
        fe.description(ep.get("description", ""))
        fe.published(ep["published"])

        audio_url = f"{base_url}/audio/{ep['filename']}"
        fe.enclosure(audio_url, str(ep.get("filesize", 0)), "audio/mpeg")
        entry_podcast: Any = getattr(fe, "podcast")
        entry_podcast.itunes_duration(ep.get("duration", 0))

    return fg.rss_str(pretty=True).decode("utf-8")


@app.get("/")
def index() -> dict:
    """Simple index endpoint."""
    episodes = load_episodes()
    info = get_programme_info()
    return {
        "title": info.title,
        "episodes": len(episodes),
        "feed_url": "/feed.xml",
    }


@app.get("/feed.xml")
def feed(request: Request) -> Response:
    """Serve the podcast RSS feed."""
    base_url = str(request.base_url).rstrip("/")
    xml = generate_feed(base_url)
    return Response(content=xml, media_type="application/rss+xml")


@app.get("/audio/{filename}")
def audio(filename: str) -> FileResponse:
    """Serve audio files with range request support."""
    file_path = AUDIO_DIR / filename
    return FileResponse(
        path=file_path,
        media_type="audio/mpeg",
        filename=filename,
    )


def main() -> None:
    """Run the uvicorn server."""
    import uvicorn

    DATA_DIR.mkdir(exist_ok=True)
    AUDIO_DIR.mkdir(exist_ok=True)
    uvicorn.run(app, host="0.0.0.0", port=5000)


if __name__ == "__main__":
    main()
