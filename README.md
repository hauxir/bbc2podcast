# bbc2podcast

Convert BBC radio programmes into self-hosted podcast RSS feeds.

Downloads episodes from BBC Sounds using yt-dlp and serves them as a podcast feed you can subscribe to in any podcast app.

## Requirements

- A UK IP address (VPN recommended)
- Python 3.14+ with [uv](https://docs.astral.sh/uv/) or Docker

## Configuration

Set the `PROGRAMME_ID` environment variable to the BBC programme ID you want to follow.

Find the programme ID in the BBC Sounds URL:
```
https://www.bbc.co.uk/programmes/b00v4tv3
                                  ^^^^^^^^
                                  this is the programme ID
```

Tested with:
- [Benji B](https://www.bbc.co.uk/programmes/b00v4tv3) (`b00v4tv3`)
- [Essential Mix](https://www.bbc.co.uk/programmes/b006ww1y) (`b006ww1y`)

## Docker (Recommended)

### Quick Start

```bash
docker run -d \
  -p 5000:5000 \
  -e PROGRAMME_ID=b00v4tv3 \
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

Download new episodes for your programme:

```bash
PROGRAMME_ID=b00v4tv3 uv run python -m bbc2podcast.update
```

### Start Server

```bash
PROGRAMME_ID=b00v4tv3 uv run uvicorn bbc2podcast.app:app --host 0.0.0.0 --port 5000
```

### Scheduled Updates

Add a cron job to update episodes automatically:

```bash
0 3 * * * cd /path/to/bbc2podcast && PROGRAMME_ID=b00v4tv3 uv run python -m bbc2podcast.update
```

## Usage

Once running, add the feed URL to your podcast app:

```
http://localhost:5000/feed.xml
```

Or if hosted on a server:

```
http://your-server:5000/feed.xml
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `/` | Status info (title, episode count) |
| `/feed.xml` | Podcast RSS feed |
| `/audio/{filename}` | Audio file streaming |

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
