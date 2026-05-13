from functools import partial
import json
import importlib.util
from zoneinfo import ZoneInfo
from selectolax.parser import HTMLParser

try:
    from .utils import Cache, Time, get_logger, leagues, network
except ImportError:
    spec = importlib.util.spec_from_file_location("utils", "utils.py")
    utils = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(utils)

    Cache = utils.Cache
    Time = utils.Time
    get_logger = utils.get_logger
    leagues = utils.leagues
    network = utils.network

log = get_logger(__name__)

urls = {}

TAG = "STRMCNTR"
CACHE_FILE = Cache(TAG, exp=86400)

API_URL = "https://backend.streamcenter.live/api/Parties"

CATEGORIES = {
    4: "Basketball",
    9: "Football",
    13: "Baseball",
    15: "Motor Sport",
    16: "Hockey",
    17: "Fight MMA",
    18: "Boxing",
    20: "WWE",
    21: "Tennis",
}


async def process_event(url: str, url_num: int):
    response = await network.request(url, log=log)

    if not response:
        log.warning(f"URL {url_num}) Failed to load url.")
        return None

    soup = HTMLParser(response.content)

    iframe = soup.css_first("iframe")

    if not iframe:
        log.warning(f"URL {url_num}) No iframe found")
        return None

    iframe_src = iframe.attributes.get("src")

    if not iframe_src:
        return None

    m3u8_id = iframe_src.rsplit("=", 1)[-1]

    m3u8_url = f"https://mainstreams.pro/hls/{m3u8_id}.m3u8"

    return {
        "url": m3u8_url,
        "referer": "https://streamcenter.xyz/",
        "origin": "https://streamcenter.xyz",
    }


async def get_events():
    events = []

    response = await network.request(
        API_URL,
        params={"pageNumber": 1, "pageSize": 500},
        log=log,
    )

    if not response:
        return events

    api_data = response.json()

    if not api_data:
        return events

    now = Time.now()

    for stream_group in api_data:
        category_id = stream_group.get("categoryId")
        name = stream_group.get("gameName")
        iframe = stream_group.get("videoUrl")
        event_time = stream_group.get("beginPartie")

        if not all([category_id, name, iframe, event_time]):
            continue

        event_dt = Time.from_str(event_time, timezone="Europe/Paris")

        if event_dt.date() != now.astimezone(ZoneInfo("Europe/Paris")).date():
            continue

        sport = CATEGORIES.get(category_id)

        if not sport:
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
