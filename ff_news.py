#!/usr/bin/env python3
"""
ForexFactory News / Latest Stories scraper.
Bypasses Cloudflare by using a real headless Chromium (Playwright).

Usage:
  python3 ff_news.py                  # one-shot, prints to stdout
  python3 ff_news.py --watch 30       # poll every 30s, print only NEW items
  python3 ff_news.py --json           # one-shot, output as JSON

Install deps (one time):
  pip3 install playwright --break-system-packages
  python3 -m playwright install chromium
"""
import argparse, json, re, sys, time
from datetime import datetime

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("ERROR: playwright not installed. Run:")
    print("  pip3 install playwright --break-system-packages")
    print("  python3 -m playwright install chromium")
    sys.exit(1)

# ── Playwright setup ─────────────────────────────────────────────────────────
LAUNCH_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox",
    "--disable-dev-shm-usage",
]
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0.0.0 Safari/537.36")

EXTRACT_JS = """() => {
    const results = [];
    // Each news item is .news-block__item
    document.querySelectorAll('.news-block__item').forEach(item => {
        // Title + URL from .news-block__image-link
        const titleEl = item.querySelector('.news-block__image-link');
        if (!titleEl) return;
        const title = titleEl.title || titleEl.innerText.trim();
        const url   = titleEl.href;
        if (!title || title.length < 5) return;

        // Source from the /hit link (rel=nofollow) — strip "From " prefix
        const sourceEl = item.querySelector('a[href*="/hit"]');
        const source = sourceEl
            ? sourceEl.innerText.replace(/^From\\s*/i, '').trim()
            : '';

        // Time from .nowrap span (has a tooltip with full datetime)
        const timeEl = item.querySelector('.nowrap');
        const ago   = timeEl ? timeEl.innerText.trim() : '';
        const datetime = timeEl ? (timeEl.title || '') : '';

        // Comments link
        const cmtEl = item.querySelector('a[href*="#comments"]');
        const comments = cmtEl ? cmtEl.innerText.trim() : '';

        // Preview text
        const previewEl = item.querySelector('.news-block__preview');
        const preview = previewEl ? previewEl.innerText.trim() : '';

        results.push({ title, url, source, ago, datetime, comments, preview });
    });
    return results;
}"""


FULL_BODY_JS = """() => {
    // The article body is in section.content.news > #newsStory
    // On Vue-rendered pages this exists; on server-rendered it may be empty
    const story = document.querySelector('#newsStory');
    const section = document.querySelector('section.content.news, section.content');
    const el = story || section || document.querySelector('.content.news') || document.querySelector('.content');
    if (!el) return '';
    let text = el.innerText || '';
    // Cut off at comment/sidebar section markers
    const cutoffs = [
        'Comment Options', 'Sort Comments By:', 'Non-English comments',
        'Add Image:', 'Attached Images', 'traders viewing now',
        'Older Stories', 'Newer Stories', 'Story Stats',
        'Related News', 'Comments / Top'
    ];
    for (const cut of cutoffs) {
        const idx = text.indexOf(cut);
        if (idx > 50) text = text.slice(0, idx);
    }
    return text.trim().replace(/\\n{3,}/g, '\\n\\n');
}"""


def fetch_full_body_fresh(playwright_instance, url: str) -> str:
    """Open a fresh browser, go directly to the article URL as the FIRST navigation
    (Cloudflare doesn't block /news/* URLs when opened fresh), extract body."""
    browser = None
    try:
        browser = playwright_instance.chromium.launch(
            headless=True, args=["--disable-blink-features=AutomationControlled","--no-sandbox"])
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="en-US", viewport={"width": 1280, "height": 720})
        ctx.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        art = ctx.new_page()
        art.goto(url, wait_until="domcontentloaded", timeout=20000)
        try:
            art.wait_for_function("document.title !== 'Just a moment...'", timeout=8000)
        except Exception:
            pass
        if "Just a moment" in art.title():
            return ""
        try:
            art.wait_for_selector("#newsStory, section.content", timeout=5000)
        except Exception:
            pass
        body = art.evaluate(FULL_BODY_JS)
        return body.strip() if body and body.strip() else ""
    except Exception as e:
        return f"[fetch error: {e}]"
    finally:
        if browser:
            browser.close()


def scrape(page, initial=False) -> list[dict]:
    """Extract news items from the ForexFactory homepage."""
    if not initial:
        page.goto("https://www.forexfactory.com/", wait_until="domcontentloaded", timeout=30000)
    # Wait for the first news item to be rendered by Vue (max 10s)
    try:
        page.wait_for_selector(".news-block__item", timeout=10000)
    except Exception:
        pass  # fall through and try anyway
    items = page.evaluate(EXTRACT_JS)
    for item in items:
        item["fetched_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    return items


def print_items(items: list[dict]):
    print(f"\n{'='*70}")
    print(f"ForexFactory — News / Latest Stories  [{datetime.now().strftime('%H:%M:%S')}]")
    print(f"{'='*70}")
    for i, it in enumerate(items, 1):
        print(f"[{i}] {it['title']}")
        if it.get('source'):   print(f"     Source  : {it['source']}")
        if it.get('ago'):      print(f"     Time    : {it['ago']}")
        if it.get('datetime'): print(f"     DateTime: {it['datetime']}")
        if it.get('comments'): print(f"     Comments: {it['comments']}")
        if it.get('body'):
            print(f"     Full Body:")
            for line in it['body'].splitlines():
                line = line.strip()
                if line:
                    print(f"       {line}")
        elif it.get('preview'):
            print(f"     Preview : {it['preview'][:120]}")
        print(f"     URL     : {it['url']}")


def main():
    ap = argparse.ArgumentParser(description="Scrape ForexFactory latest news")
    ap.add_argument("--watch",  type=int, metavar="SECS",
                    help="Poll every N seconds and print only NEW items")
    ap.add_argument("--json",   action="store_true",
                    help="Output as JSON (one-shot)")
    ap.add_argument("--full",        action="store_true",
                    help="Fetch full article body for each news item")
    ap.add_argument("--full-latest", action="store_true",
                    help="Fetch full body of the latest item only, output as JSON")
    args = ap.parse_args()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=LAUNCH_ARGS)
        context = browser.new_context(user_agent=UA, locale="en-US",
                                       viewport={"width": 1280, "height": 720})
        context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        page = context.new_page()

        # First load — solve Cloudflare, then wait for actual page content
        print("Opening ForexFactory...", file=sys.stderr)
        # Solve CF for both the homepage (/) and news paths (/news/*) upfront
        page.goto("https://www.forexfactory.com/", wait_until="domcontentloaded", timeout=30000)
        try:
            page.wait_for_function("document.title !== 'Just a moment...'", timeout=10000)
        except Exception:
            pass
        if "Just a moment" in page.title():
            print("ERROR: Cloudflare blocking. Try again.", file=sys.stderr)
            sys.exit(1)
        print("Connected!", file=sys.stderr)

        def enrich(items):
            """If --full, fetch each article body using a fresh browser per article.
            Fresh browsers bypass CF's per-URL bot detection on /news/* paths."""
            if not args.full:
                return items
            for it in items:
                print(f"  fetching: {it['title'][:60]}...", file=sys.stderr)
                body = fetch_full_body_fresh(p, it["url"])
                if body and len(body) > 100 and not body.startswith("[fetch error"):
                    it["body"] = body
            return items

        if args.full_latest:
            items = scrape(page, initial=True)
            if items:
                latest = items[0]
                body = fetch_full_body_fresh(p, latest["url"])
                if body and len(body) > 100 and not body.startswith("[fetch error"):
                    latest["body"] = body
                print(json.dumps(latest, indent=2))
        elif args.json:
            items = enrich(scrape(page, initial=True))
            print(json.dumps(items, indent=2))
        elif args.watch:
            seen_urls = set()
            items = enrich(scrape(page, initial=True))
            new_items = [it for it in items if it["url"] not in seen_urls]
            if new_items:
                print_items(new_items)
                for it in new_items:
                    seen_urls.add(it["url"])
            while True:
                time.sleep(args.watch)
                items = scrape(page)
                new_items = [it for it in items if it["url"] not in seen_urls]
                if new_items:
                    print_items(enrich(new_items))
                    for it in new_items:
                        seen_urls.add(it["url"])
                else:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] no new items", file=sys.stderr)
        else:
            items = enrich(scrape(page, initial=True))
            print_items(items)

        browser.close()


if __name__ == "__main__":
    main()
