# douban-scraper

🇨🇳 [简体中文](README.zh-CN.md)

[![Python](https://img.shields.io/badge/python-%E2%89%A53.10-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Export your Douban movies, books, music, and broadcasts to JSON. Uses the Frodo mobile API and Rexxar API directly. No browser automation, no Selenium, no login required for most data.

## Features

- Export movies, books, music, and broadcasts to JSON
- Resumable. Interrupted scrapes pick up where they left off
- Convert exported data to CSV with `to-csv`
- No authentication needed for movies, books, and music
- Built-in rate limiting to avoid hitting API thresholds

## Installation

```bash
git clone https://github.com/ritetsu/douban-scraper.git
cd douban-scraper
pip install -e .
```

For development (includes pytest, ruff):

```bash
pip install -e ".[dev]"
```

Requires Python 3.10+.

## Quick Start

```bash
# Export your Douban collection
douban-scraper export --user 123456789 --types movie,book --output ./my-data

# Convert to CSV
douban-scraper to-csv --input ./my-data
```

## Commands

### `export`

Exports user collection data from Douban. Writes JSON files to the output directory.

```bash
douban-scraper export --user 123456789 --types movie,book,music --output ./my-data
```

### `to-csv`

Converts exported JSON files into a single `douban_export.csv`. Only processes `movies.json` and `books.json` (not `music.json` or `broadcasts.json`).

```bash
douban-scraper to-csv --input ./my-data
```

Output columns: title, type, my_rating, comment, create_time, year, genres, douban_rating, card_subtitle, url, tags.

## Authentication

### Movies / Books / Music (no auth)

These go through the Frodo mobile API. The tool ships with a built-in API key and HMAC-SHA1 signing. No login or credentials required for public profile data.

### Broadcasts (cookie required)

Broadcasts use the Rexxar API, which requires a valid `ck` cookie from an authenticated browser session.

```bash
douban-scraper export --user 123456789 --types broadcast --cookie "YOUR_CK_VALUE" --output ./my-data
```

Pass the raw `ck` value only. The code prepends `ck=` automatically.

To find your `ck` cookie:

1. Log in to Douban in your browser
2. Open Developer Tools (F12 or Ctrl+Shift+I)
3. Go to the **Application** tab (Chrome) or **Storage** tab (Firefox)
4. Under **Cookies**, select `m.douban.com`
5. Copy the value of the cookie named `ck`

## Output Format

The tool writes one JSON file per content type to the output directory:

| File | Contents |
|------|----------|
| `movies.json` | Movie ratings and comments |
| `books.json` | Book ratings and comments |
| `music.json` | Music ratings and comments |
| `broadcasts.json` | Broadcast/miniblog posts |

Note: `music.json` is singular, not `musics.json`.

A `.progress.json` file tracks scraping state for resumability.

Example movie entry:

```json
{
  "comment": "Rewatched this again, still holds up.",
  "rating": {
    "value": 5,
    "max": 5
  },
  "create_time": "2024-08-12 22:31:17",
  "subject": {
    "id": "35290178",
    "title": "奥本海默",
    "url": "https://movie.douban.com/subject/35290178/",
    "cover": "https://img2.doubanio.com/view/photo/s_ratio_poster/public/p2895451952.jpg",
    "rating": {
      "value": 8.9
    },
    "type": "movie",
    "year": "2023",
    "genres": ["剧情", "传记", "历史"],
    "card_subtitle": "2023 / 美国 英国 / 剧情 传记 历史 / 克里斯托弗·诺兰 / 基里安·墨菲 艾米莉·布朗特"
  },
  "status": "done",
  "tags": ["诺兰", "历史", "2023"]
}
```

Example broadcast entry:

```json
{
  "id": "abc123",
  "text": "Just finished reading this. Highly recommended.",
  "created_at": "2024-07-20 14:05:00",
  "comments_count": 3,
  "likes_count": 12,
  "subject": null,
  "reshared_status": null
}
```

## Configuration

| Flag | Required | Default | Description |
|------|----------|---------|-------------|
| `--user` / `-u` | Yes | | Douban user ID (numeric) |
| `--types` / `-t` | No | `movie,book,music` | Comma-separated: `movie`, `book`, `music`, `broadcast` |
| `--status` / `-s` | No | `done` | Comma-separated statuses: `done`, `doing`, `mark`, or `all` |
| `--output` / `-o` | No | `./output` | Output directory |
| `--cookie` / `-c` | For broadcasts | | Raw `ck` cookie value (not `ck=VALUE`) |
| `--delay` / `-d` | No | `1.5` | Delay between requests (seconds) |
| `--max-items` / `-m` | No | `0` | Max items per type/status (0 = unlimited) |
| `--api-key` | No | built-in | Override Frodo API key |
| `--api-secret` | No | built-in | Override Frodo HMAC secret |
| `--force` / `-f` | No | `false` | Re-scrape and overwrite existing output |

## Limitations

- Long-form reviews (评论/影评) are not supported. There is no API endpoint, and Douban's web pages are protected by proof-of-work challenges
- Game collections are not supported in v1
- Private profile data is not supported
- `to-csv` only processes `movies.json` and `books.json` (not music or broadcasts)
- `--force` deletes **all** `.json` files in the output directory, including any custom files you may have added

## Finding Your User ID

Your Douban user ID is the numeric part of your profile URL. Open your profile page and look at the URL:

```
https://www.douban.com/people/123456789/
```

The number `123456789` is your user ID. Pass it with `--user 123456789`.

## Contributing

Open an issue to discuss changes. Fork the repo and submit a pull request. Run `pytest` before submitting. Code style is enforced with `ruff`.

## Disclaimer

This project is not affiliated with Douban. Use responsibly and respect rate limits.

## License

MIT &copy; 2026 ritetsu. See [LICENSE](LICENSE) for details.
