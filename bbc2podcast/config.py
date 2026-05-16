"""Configuration from environment variables."""

import html
import os
import re
import shutil
import urllib.request
from dataclasses import dataclass
from functools import cache
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"

# Legacy paths (pre multi-programme support). Kept for backwards-compatible reads
# and one-time migration into the per-programme layout.
LEGACY_EPISODES_FILE = DATA_DIR / "episodes.json"
LEGACY_AUDIO_DIR = DATA_DIR / "audio"


def _parse_programme_ids() -> list[str]:
    """Parse PROGRAMME_IDS (comma-separated) with PROGRAMME_ID as single fallback."""
    raw = os.environ.get("PROGRAMME_IDS") or os.environ.get("PROGRAMME_ID", "b00v4tv3")
    ids = [pid.strip() for pid in raw.split(",") if pid.strip()]
    return ids or ["b00v4tv3"]


PROGRAMME_IDS = _parse_programme_ids()
# First programme acts as the default for legacy /feed.xml and /audio/ routes.
DEFAULT_PROGRAMME_ID = PROGRAMME_IDS[0]

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
)


def programme_dir(programme_id: str) -> Path:
    """Directory holding episodes.json and audio/ for a programme."""
    return DATA_DIR / programme_id


def episodes_file(programme_id: str) -> Path:
    return programme_dir(programme_id) / "episodes.json"


def audio_dir(programme_id: str) -> Path:
    return programme_dir(programme_id) / "audio"


def migrate_legacy_data() -> None:
    """One-time migration of pre-multi-programme data into the default programme.

    Moves data/episodes.json and data/audio/ into data/{DEFAULT_PROGRAMME_ID}/
    if the default programme directory has no episodes file yet.
    """
    default_dir = programme_dir(DEFAULT_PROGRAMME_ID)
    new_episodes = episodes_file(DEFAULT_PROGRAMME_ID)
    new_audio = audio_dir(DEFAULT_PROGRAMME_ID)

    has_legacy = LEGACY_EPISODES_FILE.exists() or LEGACY_AUDIO_DIR.is_dir()
    if not has_legacy or new_episodes.exists():
        return

    default_dir.mkdir(parents=True, exist_ok=True)

    if LEGACY_EPISODES_FILE.exists():
        shutil.move(str(LEGACY_EPISODES_FILE), str(new_episodes))

    if LEGACY_AUDIO_DIR.is_dir():
        new_audio.mkdir(parents=True, exist_ok=True)
        for entry in LEGACY_AUDIO_DIR.iterdir():
            target = new_audio / entry.name
            if not target.exists():
                shutil.move(str(entry), str(target))
        try:
            LEGACY_AUDIO_DIR.rmdir()
        except OSError:
            pass


@dataclass
class ProgrammeInfo:
    """Programme metadata from BBC."""

    id: str
    title: str
    description: str
    image_url: str | None


@cache
def get_programme_info(programme_id: str) -> ProgrammeInfo:
    """Fetch programme metadata from BBC. Results are cached."""
    url = f"https://www.bbc.co.uk/programmes/{programme_id}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=30) as response:
            page_html = response.read().decode("utf-8")
    except Exception:
        return ProgrammeInfo(
            id=programme_id,
            title=f"BBC Programme {programme_id}",
            description="",
            image_url=None,
        )

    # Extract title from <title> tag
    title_match = re.search(r"<title>([^<]+)</title>", page_html)
    title = title_match.group(1).split(" - BBC")[0] if title_match else programme_id
    title = html.unescape(title)

    # Extract description from meta tag
    desc_match = re.search(r'<meta name="description" content="([^"]+)"', page_html)
    description = html.unescape(desc_match.group(1)) if desc_match else ""

    # Extract image URL
    img_match = re.search(r'<meta property="og:image" content="([^"]+)"', page_html)
    image_url = img_match.group(1) if img_match else None

    return ProgrammeInfo(
        id=programme_id,
        title=title,
        description=description,
        image_url=image_url,
    )
