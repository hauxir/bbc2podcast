# bbc2podcast

Convert BBC radio programmes into self-hosted podcast RSS feeds.

Downloads episodes from BBC Sounds using yt-dlp and serves them as a podcast feed you can subscribe to in any podcast app.

## Requirements

- A UK IP address (VPN recommended)
- Python 3.14+ with [uv](https://docs.astral.sh/uv/) or Docker

## Configuration

Set `PROGRAMME_IDS` to a comma-separated list of BBC programme IDs you want to follow. For a single programme you can use `PROGRAMME_ID` instead (kept for backwards compatibility).

Find the programme ID in the BBC Sounds URL:
```
https://www.bbc.co.uk/programmes/b00v4tv3
                                  ^^^^^^^^
                                  this is the programme ID
```

Multiple programmes example:
```
PROGRAMME_IDS=b00v4tv3,b006ww1y
```

Each programme gets its own feed at `/{programme_id}/feed.xml`. The first programme is also exposed at the legacy `/feed.xml` URL so existing subscriptions keep working.

Tested with:
- [Benji B](https://www.bbc.co.uk/programmes/b00v4tv3) (`b00v4tv3`)
- [Essential Mix](https://www.bbc.co.uk/programmes/b006ww1y) (`b006ww1y`)

## Docker (Recommended)

### Quick Start

```bash
docker run -d \
  -p 5000:5000 \
  -e PROGRAMME_IDS=b00v4tv3,b006ww1y \
  -v ./data:/app/data \
  ghcr.io/hauxir/bbc2podcast:latest
```

### With VPN (Required for non-UK users)

Copy the example compose file and configure your VPN:

```bash
cp docker-compose.yml.example docker-compose.yml
```

Edit `docker-compose.yml` and configure the gluetun VPN settings for your provider (see [gluetun wiki](https://github.com/qdm12/gluetun-wiki)).

Then start the services:

```bash
docker compose up -d
```

The compose setup includes:
- **gluetun**: VPN container routing traffic through a UK server
- **bbc2podcast**: The podcast server
- **ofelia**: Scheduler that updates episodes daily at 3 AM

### Manual Episode Update

```bash
docker compose exec bbc2podcast uv run python -m bbc2podcast.update
```

## Without Docker

### Install

```bash
git clone https://github.com/hauxir/bbc2podcast.git
cd bbc2podcast
uv sync
```

### Update Episodes

Download new episodes for your programmes:

```bash
PROGRAMME_IDS=b00v4tv3,b006ww1y uv run python -m bbc2podcast.update
```

### Start Server

```bash
PROGRAMME_IDS=b00v4tv3,b006ww1y uv run uvicorn bbc2podcast.app:app --host 0.0.0.0 --port 5000
```

### Scheduled Updates

Add a cron job to update episodes automatically:

```bash
0 3 * * * cd /path/to/bbc2podcast && PROGRAMME_IDS=b00v4tv3,b006ww1y uv run python -m bbc2podcast.update
```

## Usage

Once running, add the feed URL for each programme to your podcast app:

```
http://localhost:5000/b00v4tv3/feed.xml
http://localhost:5000/b006ww1y/feed.xml
```

Or visit `http://localhost:5000/` to see all configured programmes.

The legacy `/feed.xml` URL still works and serves the first programme in `PROGRAMME_IDS`.

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `/` | Status info — lists configured programmes |
| `/{programme_id}/feed.xml` | Podcast RSS feed for a programme |
| `/{programme_id}/audio/{filename}` | Audio file streaming |
| `/feed.xml` | Legacy alias for the first programme's feed |
| `/audio/{filename}` | Legacy alias for the first programme's audio |

## Development

```bash
# Install with dev dependencies
uv sync

# Run linting
uv run ruff check .
uv run ruff format --check .

# Run type checking
uv run basedpyright
```
