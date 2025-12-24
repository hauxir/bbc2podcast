"""Download and update BBC programme episodes using yt-dlp."""

import json
import re
import subprocess
import sys
import urllib.request
from datetime import UTC, datetime

from bbc2podcast.config import (
    AUDIO_DIR,
    DATA_DIR,
    EPISODES_FILE,
    PROGRAMME_ID,
    USER_AGENT,
)


def load_episodes() -> list[dict]:
    """Load existing episode metadata, deduplicating by ID."""
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


def save_episodes(episodes: list[dict]) -> None:
    """Save episode metadata to JSON."""
    with open(EPISODES_FILE, "w") as f:
        json.dump(episodes, f, indent=2)


def get_available_episodes() -> list[str]:
    """Fetch list of available episode IDs by scraping BBC programmes page."""
    url = f"https://www.bbc.co.uk/programmes/{PROGRAMME_ID}/episodes/player"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=30) as response:
            html = response.read().decode("utf-8")
    except Exception as e:
        print(f"Error fetching episodes page: {e}", file=sys.stderr)
        return []

    # Extract episode PIDs from data-pid attributes
    pids = re.findall(r'data-pid="([^"]+)"', html)
    # Filter out programme ID and deduplicate while preserving order
    seen: set[str] = set()
    episode_ids: list[str] = []
    for pid in pids:
        if pid != PROGRAMME_ID and pid not in seen:
            seen.add(pid)
            episode_ids.append(pid)

    return episode_ids


def download_episode(episode_id: str) -> dict | None:
    """Download a single episode and return its metadata."""
    url = f"https://www.bbc.co.uk/programmes/{episode_id}"
    output_template = str(AUDIO_DIR / "%(id)s.%(ext)s")

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
            audio_file = AUDIO_DIR / f"{info['id']}.mp3"

            if not audio_file.exists():
                for ext in ["m4a", "webm", "opus", "ogg"]:
                    alt_file = AUDIO_DIR / f"{info['id']}.{ext}"
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


def update_episodes() -> None:
    """Update episode library with new episodes."""
    DATA_DIR.mkdir(exist_ok=True)
    AUDIO_DIR.mkdir(exist_ok=True)

    existing = load_episodes()
    existing_ids = {ep["id"] for ep in existing}

    print("Fetching available episodes...")
    available_ids = get_available_episodes()
    print(f"Found {len(available_ids)} available episodes")

    new_count = 0
    for episode_id in available_ids:
        if episode_id in existing_ids:
            continue

        print(f"Downloading: {episode_id}")
        metadata = download_episode(episode_id)
        if metadata:
            existing.append(metadata)
            existing_ids.add(episode_id)
            new_count += 1
            save_episodes(existing)
            print(f"  -> {metadata['title']}")

    print(f"Downloaded {new_count} new episodes")
    print(f"Total episodes: {len(existing)}")


def main() -> None:
    """Entry point for update script."""
    update_episodes()


if __name__ == "__main__":
    main()
