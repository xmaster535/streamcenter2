from functools import partial
import json
import importlib.util

# Import selectolax
from selectolax.parser import HTMLParser

# Try relative import first (for package), fallback to absolute
try:
    from .utils import Cache, Time, get_logger, leagues, network
except ImportError:
    # For direct execution or GitHub Actions
    spec = importlib.util.spec_from_file_location("utils", "utils.py")
    utils = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(utils)
    Cache = utils.Cache
    Time = utils.Time
    get_logger = utils.get_logger
    leagues = utils.leagues
    network = utils.network

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
    """Export URLs as JSON string in app format."""
    return json.dumps(export_to_list(), indent=2)


def export_to_file(filepath: str = "streams.json") -> None:
    """Export URLs to JSON file."""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(export_to_list(), f, indent=2)
    log.info(f"Exported {len(urls)} streams to {filepath}")


def export_to_list() -> list:
    """Convert URLs dict to app-compatible list format."""
    result = []
    for key, data in urls.items():
        # Parse sport from key [Sport] Event (TAG)
        sport = key.split("]")[0].replace("[", "").strip()

        # Get time from timestamp
        ts = data.get("timestamp", 0)
        from datetime import datetime, timezone
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        time_str = dt.strftime("%H:%M:%S")
        date_str = dt.strftime("%d/%m/%Y")

        # Build full link with headers
        m3u8_url = data.get("url", "")
        referer = data.get("referer", "https://streamcenter.xyz")
        origin = data.get("origin", "https://streamcenter.xyz")

        full_link = (
            f"{m3u8_url}"
            f"|User-Agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            f"(KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0"
            f"&Referer={referer}"
            f"&Origin={origin}"
        )

        # Get event name without sport tag
        event_name = key.split("]")[1].replace(f"({TAG})", "").strip()

        # Calculate end time (1 hour after start)
        from datetime import timedelta
        end_dt = dt + timedelta(hours=1)
        end_time_str = end_dt.strftime("%H:%M:%S")
        end_date_str = end_dt.strftime("%d/%m/%Y")

        entry = {
            "category": "Live Events",
            "date": date_str,
            "end_date": end_date_str,
            "end_time": end_time_str,
            "eventName": event_name,
            "link_names": ["DlSports"],
            "streaming_links": [
                {
                    "api": "",
                    "link": full_link,
                    "name": "DlSports"
                }
            ],
            "teamAFlag": "https://github.com/falconcasthoster/images/blob/main/FalconCast.png?raw=true",
            "teamAName": f"[{sport}] {event_name}",
            "teamBFlag": "https://github.com/falconcasthoster/images/blob/main/FalconCast.png?raw=true",
            "teamBName": "",
            "time": time_str
        }
        result.append(entry)

    return result


def export_m3u() -> str:
    """Export URLs as M3U playlist with referer and origin headers."""
    lines = ["#EXTM3U", ""]
    for key, data in urls.items():
        sport = key.split("]")[0].replace("[", "").strip()
        event_name = key.split("]")[1].replace(f"({TAG})", "").strip()
        m3u8_url = data.get("url", "")
        referer = data.get("referer", "https://streamcenter.xyz")
        origin = data.get("origin", "https://streamcenter.xyz")

        if m3u8_url:
            full_link = (
                f"{m3u8_url}"
                f"|User-Agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                f"(KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0"
                f"&Referer={referer}"
                f"&Origin={origin}"
            )
            lines.append(f'#EXTINF:-1 tvg-name="{event_name}" tvg-id="{sport}" group-title="Live Sports",{event_name}')
            lines.append(full_link)

    return "\n".join(lines)


def export_m3u_to_file(filepath: str = "streams.m3u") -> None:
    """Export URLs to M3U playlist file."""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(export_m3u())
    log.info(f"Exported {len(urls)} streams to {filepath}")

