from functools import partial
import json

from selectolax.parser import HTMLParser

from .utils import Cache, Time, get_logger, leagues, network

log = get_logger(__name__)

urls: dict[str, dict[str, str | float]] = {}

TAG = "STRMCNTR"

CACHE_FILE = Cache(TAG, exp=86_400)

API_URL = "https://backend.streamcenter.live/api/Parties"

CATEGORIES = {
    4: "Basketball",
    9: "Football",
    13: "Baseball",
    # 14: "American Football",
    15: "Motor Sport",
    16: "Hockey",
    17: "Fight MMA",
    18: "Boxing",
    20: "WWE",
    21: "Tennis",
}


async def process_event(url: str, url_num: int) -> dict | None:
    if not (html_data := await network.request(url, log=log)):
        log.warning(f"URL {url_num}) Failed to load url.")
        return None

    soup = HTMLParser(html_data.content)

    iframe = soup.css_first("iframe")

    if not iframe or not (iframe_src := iframe.attributes.get("src")):
        log.warning(f"URL {url_num}) No iframe element found.")
        return None

    log.info(f"URL {url_num}) Captured M3U8")

    m3u8_id = iframe_src.rsplit("=", 1)[-1]
    m3u8_url = f"https://mainstreams.pro/hls/{m3u8_id}.m3u8"

    # Fixed referer and origin for streamcenter.xyz
    referer_url = "https://streamcenter.xyz/"
    origin = "https://streamcenter.xyz"

    return {
        "url": m3u8_url,
        "referer": referer_url,
        "origin": origin,
    }


async def get_events() -> list[dict[str, str]]:
    events = []

    if not (
        r := await network.request(
            API_URL,
            params={"pageNumber": 1, "pageSize": 500},
            log=log,
        )
    ):
        return events

    now = Time.clean(Time.now())

    api_data: list[dict] = r.json()

    for stream_group in api_data:
        category_id: int = stream_group.get("categoryId")

        name: str = stream_group.get("gameName")

        iframe: str = stream_group.get("videoUrl")

        event_time: str = stream_group.get("beginPartie")

        if not (name and category_id and iframe and event_time):
            continue

        event_dt = Time.from_str(event_time, timezone="CET")

        if event_dt.date() != now.date():
            continue

        if not (sport := CATEGORIES.get(category_id)):
            continue

        events.append(
            {
                "sport": sport,
                "event": name,
                "link": iframe.split("<")[0],
                "timestamp": now.timestamp(),
            }
        )

    return events


async def scrape() -> None:
    cached_urls = CACHE_FILE.load()

    if cached_urls and urls.update({k: v for k, v in cached_urls.items() if v.get("url")}):
        log.info(f"Loaded {len(urls)} event(s) from cache")

        return

    log.info('Scraping from "https://streamcenter.xyz"')

    if events := await get_events():
        log.info(f"Processing {len(events)} URL(s)")

        for i, ev in enumerate(events, start=1):
            handler = partial(
                process_event,
                url=(link := ev["link"]),
                url_num=i,
            )

            url_data = await network.safe_process(
                handler,
                url_num=i,
                semaphore=network.HTTP_S,
                log=log,
            )

            sport, event, ts = (
                ev["sport"],
                ev["event"],
                ev["timestamp"],
            )

            key = f"[{sport}] {event} ({TAG})"

            tvg_id, logo = leagues.get_tvg_info(sport, event)

            entry = {
                "url": url_data.get("url") if url_data else None,
                "referer": url_data.get("referer") if url_data else None,
                "origin": url_data.get("origin") if url_data else None,
                "logo": logo,
                "base": "https://streamcenter.xyz",
                "timestamp": ts,
                "id": tvg_id or "Live.Event.us",
                "link": link,
            }

            cached_urls[key] = entry

            if url_data and url_data.get("url"):
                urls[key] = entry

        log.info(f"Collected and cached {len(urls)} event(s)")

    else:
        log.info("No events found")

    CACHE_FILE.write(cached_urls)


def export() -> str:
    """Export URLs as JSON string."""
    return json.dumps(urls, indent=2)


def export_to_file(filepath: str = "streams.json") -> None:
    """Export URLs to JSON file."""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(urls, f, indent=2)
    log.info(f"Exported {len(urls)} streams to {filepath}")

