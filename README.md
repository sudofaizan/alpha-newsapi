# alpha-newsapi

Live ForexFactory news scraper — bypasses Cloudflare using headless Chromium.

## Quick start (Amazon Linux 2)

```bash
git clone https://github.com/sudofaizan/alpha-newsapi.git
cd alpha-newsapi
bash deploy.sh
```

## Usage

```bash
# Latest 5 headlines
python3 ff_news.py

# Latest item only — full body as JSON (fastest, ~3s)
python3 ff_news.py --full-latest

# All items with full body text
python3 ff_news.py --full

# All items as JSON array
python3 ff_news.py --json

# Watch mode — poll every 60s, print only NEW items
python3 ff_news.py --watch 60

# Watch + full body on new items
python3 ff_news.py --watch 60 --full
```
# alpha-newsapi
# alpha-newsapi
# alpha-newsapi
