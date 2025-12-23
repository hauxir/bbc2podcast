"""Configuration from environment variables."""

import html
import os
import re
import urllib.request
from dataclasses import dataclass
from functools import cache
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
EPISODES_FILE = DATA_DIR / "episodes.json"
AUDIO_DIR = DATA_DIR / "audio"

# Default to Benji B if not set
PROGRAMME_ID = os.environ.get("PROGRAMME_ID", "b00v4tv3")

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
)


@dataclass
class ProgrammeInfo:
    """Programme metadata from BBC."""

    id: str
    title: str
    description: str
    image_url: str | None


@cache
def get_programme_info() -> ProgrammeInfo:
    """Fetch programme metadata from BBC. Results are cached."""
    url = f"https://www.bbc.co.uk/programmes/{PROGRAMME_ID}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=30) as response:
            page_html = response.read().decode("utf-8")
    except Exception:
        return ProgrammeInfo(
            id=PROGRAMME_ID,
            title=f"BBC Programme {PROGRAMME_ID}",
            description="",
            image_url=None,
        )

    # Extract title from <title> tag
    title_match = re.search(r"<title>([^<]+)</title>", page_html)
    title = title_match.group(1).split(" - BBC")[0] if title_match else PROGRAMME_ID
    title = html.unescape(title)

    # Extract description from meta tag
    desc_match = re.search(r'<meta name="description" content="([^"]+)"', page_html)
    description = html.unescape(desc_match.group(1)) if desc_match else ""

    # Extract image URL
    img_match = re.search(r'<meta property="og:image" content="([^"]+)"', page_html)
    image_url = img_match.group(1) if img_match else None

    return ProgrammeInfo(
        id=PROGRAMME_ID,
        title=title,
        description=description,
        image_url=image_url,
    )
