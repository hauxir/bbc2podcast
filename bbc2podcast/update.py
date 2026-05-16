"""Download and update BBC programme episodes using yt-dlp."""

import json
import re
import subprocess
import sys
import urllib.request
from datetime import UTC, datetime

from bbc2podcast.config import (
    DATA_DIR,
    PROGRAMME_IDS,
    USER_AGENT,
    audio_dir,
    episodes_file,
    migrate_legacy_data,
    programme_dir,
)


def load_episodes(programme_id: str) -> list[dict]:
    """Load existing episode metadata for a programme, deduplicating by ID."""
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


def save_episodes(programme_id: str, episodes: list[dict]) -> None:
    """Save episode metadata to JSON, deduplicating by ID."""
    seen: set[str] = set()
    unique: list[dict] = []
    for ep in episodes:
        if ep["id"] not in seen:
            seen.add(ep["id"])
            unique.append(ep)
    with open(episodes_file(programme_id), "w") as f:
        json.dump(unique, f, indent=2)


def get_available_episodes(programme_id: str) -> list[str]:
    """Fetch list of available episode IDs by scraping BBC programmes page."""
    url = f"https://www.bbc.co.uk/programmes/{programme_id}/episodes/player"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=30) as response:
            html = response.read().decode("utf-8")
    except Exception as e:
        print(f"Error fetching episodes page for {programme_id}: {e}", file=sys.stderr)
        return []

    pids = re.findall(r'data-pid="([^"]+)"', html)
    seen: set[str] = set()
    episode_ids: list[str] = []
    for pid in pids:
        if pid != programme_id and pid not in seen:
            seen.add(pid)
            episode_ids.append(pid)

    return episode_ids


def download_episode(programme_id: str, episode_id: str) -> dict | None:
    """Download a single episode and return its metadata."""
    url = f"https://www.bbc.co.uk/programmes/{episode_id}"
    out_dir = audio_dir(programme_id)
    output_template = str(out_dir / "%(id)s.%(ext)s")

    result = subprocess.run(
        [
            "yt-dlp",
            "--extract-audio",
            "--audio-format",
            "mp3",
            "--audio-quality",
            "0",
            "--output",
            output_template,
            "--print-json",
            url,
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"Error downloading {episode_id}: {result.stderr}", file=sys.stderr)
        return None

    for line in result.stdout.strip().split("\n"):
        if line.startswith("{"):
            info = json.loads(line)
            audio_file = out_dir / f"{info['id']}.mp3"

            if not audio_file.exists():
                for ext in ["m4a", "webm", "opus", "ogg"]:
                    alt_file = out_dir / f"{info['id']}.{ext}"
                    if alt_file.exists():
                        audio_file = alt_file
                        break

            filesize = audio_file.stat().st_size if audio_file.exists() else 0

            upload_date = info.get("upload_date", "")
            if upload_date:
                dt = datetime.strptime(upload_date, "%Y%m%d").replace(tzinfo=UTC)
                published = dt.isoformat()
            else:
                published = datetime.now(UTC).isoformat()

            return {
                "id": info["id"],
                "title": info.get("title", "Unknown"),
                "description": info.get("description", ""),
                "duration": info.get("duration", 0),
                "published": published,
                "filename": audio_file.name,
                "filesize": filesize,
            }

    return None


def update_programme(programme_id: str) -> None:
    """Update episode library for a single programme."""
    programme_dir(programme_id).mkdir(parents=True, exist_ok=True)
    audio_dir(programme_id).mkdir(parents=True, exist_ok=True)

    existing = load_episodes(programme_id)
    existing_ids = {ep["id"] for ep in existing}

    print(f"[{programme_id}] Fetching available episodes...")
    available_ids = get_available_episodes(programme_id)
    print(f"[{programme_id}] Found {len(available_ids)} available episodes")

    new_count = 0
    for episode_id in available_ids:
        if episode_id in existing_ids:
            continue

        print(f"[{programme_id}] Downloading: {episode_id}")
        metadata = download_episode(programme_id, episode_id)
        if metadata:
            existing.append(metadata)
            existing_ids.add(episode_id)
            new_count += 1
            save_episodes(programme_id, existing)
            print(f"[{programme_id}]   -> {metadata['title']}")

    print(f"[{programme_id}] Downloaded {new_count} new episodes")
    print(f"[{programme_id}] Total episodes: {len(existing)}")


def update_episodes() -> None:
    """Update episode libraries for all configured programmes."""
    DATA_DIR.mkdir(exist_ok=True)
    migrate_legacy_data()
    for programme_id in PROGRAMME_IDS:
        update_programme(programme_id)


def main() -> None:
    """Entry point for update script."""
    update_episodes()


if __name__ == "__main__":
    main()
