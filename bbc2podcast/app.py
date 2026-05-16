"""FastAPI app serving podcast RSS feeds and audio files."""

import json
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response
from feedgen.feed import FeedGenerator

from bbc2podcast.config import (
    DATA_DIR,
    DEFAULT_PROGRAMME_ID,
    PROGRAMME_IDS,
    audio_dir,
    episodes_file,
    get_programme_info,
    migrate_legacy_data,
    programme_dir,
)

app = FastAPI()


@app.on_event("startup")
def _startup() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    migrate_legacy_data()
    for pid in PROGRAMME_IDS:
        programme_dir(pid).mkdir(parents=True, exist_ok=True)
        audio_dir(pid).mkdir(parents=True, exist_ok=True)


def _require_programme(programme_id: str) -> None:
    if programme_id not in PROGRAMME_IDS:
        raise HTTPException(status_code=404, detail="Unknown programme")


def load_episodes(programme_id: str) -> list[dict]:
    """Load episode metadata for a programme, deduplicating by ID."""
    path = episodes_file(programme_id)
    if not path.exists():
        return []
    with open(path) as f:
        episodes = json.load(f)
    seen: set[str] = set()
    unique: list[dict] = []
    for ep in episodes:
        if ep["id"] not in seen:
            seen.add(ep["id"])
            unique.append(ep)
    return unique


def generate_feed(programme_id: str, base_url: str) -> str:
    """Generate podcast RSS feed XML for a programme."""
    episodes = load_episodes(programme_id)
    info = get_programme_info(programme_id)

    feed_url = f"{base_url}/{programme_id}/feed.xml"

    fg = FeedGenerator()
    fg.load_extension("podcast")
    podcast: Any = getattr(fg, "podcast")

    fg.id(feed_url)
    fg.title(info.title)
    fg.description(info.description)
    fg.link(href=base_url, rel="alternate")
    fg.link(href=feed_url, rel="self")
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

        audio_url = f"{base_url}/{programme_id}/audio/{ep['filename']}"
        fe.enclosure(audio_url, str(ep.get("filesize", 0)), "audio/mpeg")
        entry_podcast: Any = getattr(fe, "podcast")
        entry_podcast.itunes_duration(ep.get("duration", 0))

    return fg.rss_str(pretty=True).decode("utf-8")


@app.get("/")
def index() -> dict:
    """Status info listing all configured programmes."""
    programmes = []
    for pid in PROGRAMME_IDS:
        info = get_programme_info(pid)
        programmes.append(
            {
                "id": pid,
                "title": info.title,
                "episodes": len(load_episodes(pid)),
                "feed_url": f"/{pid}/feed.xml",
            }
        )
    return {"programmes": programmes}


@app.get("/feed.xml")
def legacy_feed(request: Request) -> Response:
    """Legacy feed URL: serves the default (first-configured) programme."""
    base_url = str(request.base_url).rstrip("/")
    xml = generate_feed(DEFAULT_PROGRAMME_ID, base_url)
    return Response(content=xml, media_type="application/rss+xml")


@app.get("/audio/{filename}")
def legacy_audio(filename: str) -> FileResponse:
    """Legacy audio URL: looks in the default programme's audio dir."""
    file_path = audio_dir(DEFAULT_PROGRAMME_ID) / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        path=file_path,
        media_type="audio/mpeg",
        filename=filename,
    )


@app.get("/{programme_id}/feed.xml")
def feed(programme_id: str, request: Request) -> Response:
    """Serve the podcast RSS feed for a programme."""
    _require_programme(programme_id)
    base_url = str(request.base_url).rstrip("/")
    xml = generate_feed(programme_id, base_url)
    return Response(content=xml, media_type="application/rss+xml")


@app.get("/{programme_id}/audio/{filename}")
def audio(programme_id: str, filename: str) -> FileResponse:
    """Serve audio files with range request support."""
    _require_programme(programme_id)
    file_path = audio_dir(programme_id) / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        path=file_path,
        media_type="audio/mpeg",
        filename=filename,
    )


def main() -> None:
    """Run the uvicorn server."""
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5000)


if __name__ == "__main__":
    main()
