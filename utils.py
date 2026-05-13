"""
StreamCenter Scraper - Utility Modules
Contains: Cache, Time, get_logger, leagues, network
"""
import json
import time
import logging
import hashlib
import aiohttp
import asyncio
from pathlib import Path
from typing import Any, Optional


# ============ Cache Module ============
class Cache:
    """Simple JSON-based cache with expiration."""

    def __init__(self, tag: str, exp: int = 3600):
        self.tag = tag
        self.exp = exp
        self.cache_dir = Path("cache")
        self.cache_dir.mkdir(exist_ok=True)
        self.cache_file = self.cache_dir / f"{tag}.json"

    def load(self) -> dict:
        """Load cache from disk if not expired."""
        if not self.cache_file.exists():
            return {}

        try:
            with open(self.cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Check expiration
            if time.time() - data.get("_timestamp", 0) > self.exp:
                return {}

            return data
        except (json.JSONDecodeError, IOError):
            return {}

    def write(self, data: dict) -> None:
        """Write cache to disk with timestamp."""
        data["_timestamp"] = time.time()
        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)


# ============ Time Module ============
class Time:
    """Time utilities for timezone handling."""

    @staticmethod
    def now() -> "Time":
        """Get current time instance."""
        t = Time()
        t.timestamp = time.time()
        return t

    def __init__(self):
        self.timestamp = 0.0

    def date(self):
        """Get date from timestamp."""
        import datetime
        return datetime.datetime.fromtimestamp(self.timestamp).date()

    @staticmethod
    def clean(t: "Time") -> "Time":
        """Clean time (reset to start of minute)."""
        t.timestamp = int(t.timestamp)
        return t

    def from_str(self, time_str: str, timezone: str = "UTC") -> "Time":
        """Parse time string to Time object."""
        from datetime import datetime
        try:
            # Try parsing ISO format
            dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
            t = Time()
            t.timestamp = dt.timestamp()
            return t
        except ValueError:
            t = Time()
            t.timestamp = time.time()
            return t


# ============ Logger Module ============
def get_logger(name: str) -> logging.Logger:
    """Get configured logger instance."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)s - %(message)s",
            datefmt="%H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


# ============ Network Module ============
class Network:
    """Async HTTP client with rate limiting."""

    HTTP_S = asyncio.Semaphore(3)  # Max concurrent requests

    @staticmethod
    async def request(
        url: str,
        method: str = "GET",
        params: dict = None,
        headers: dict = None,
        log=None,
        timeout: int = 30,
    ) -> Optional[dict]:
        """Make async HTTP request and return JSON data."""
        timeout_obj = aiohttp.ClientTimeout(total=timeout)

        async with aiohttp.ClientSession(timeout=timeout_obj) as session:
            try:
                async with session.request(
                    method,
                    url,
                    params=params,
                    headers=headers,
                ) as response:
                    if response.status == 200:
                        # Await the json() coroutine - THIS WAS THE FIX
                        data = await response.json()
                        return data
                    elif log:
                        log.warning(f"Request failed: {response.status}")
                    return None
            except Exception as e:
                if log:
                    log.warning(f"Request error: {e}")
                return None

    @staticmethod
    async def safe_process(
        handler,
        url_num: int,
        semaphore,
        log=None,
        retries: int = 2,
    ) -> Any:
        """Execute handler with semaphore and retry logic."""
        async with semaphore:
            for attempt in range(retries):
                try:
                    return await handler()
                except Exception as e:
                    if log and attempt == retries - 1:
                        log.warning(f"URL {url_num}) Error after {retries} attempts: {e}")
                    elif log:
                        log.info(f"URL {url_num}) Retry {attempt + 1}/{retries}")
                    await asyncio.sleep(1)
            return None


# ============ Leagues Module ============
class Leagues:
    """Team logo and EPG info database."""

    # Sport-specific team logos and EPG mappings
    DATA = {
        "Football": {
            "Manchester City": ("382", "https://a.espncdn.com/i/teamlogos/soccer/500/382.png"),
            "Barcelona": ("83", "https://a.espncdn.com/i/teamlogos/soccer/500/83.png"),
            "Real Madrid": ("86", "https://a.espncdn.com/i/teamlogos/soccer/500/86.png"),
            "PSG": ("160", "https://a.espncdn.com/i/teamlogos/soccer/500/160.png"),
            "Liverpool": ("231", "https://a.espncdn.com/i/teamlogos/soccer/500/231.png"),
        },
        "Basketball": {
            "Lakers": ("1610609947", "https://a.espncdn.com/i/teamlogos/nba/500/scoreboard/lal.png"),
            "Warriors": ("1610612744", "https://a.espncdn.com/i/teamlogos/nba/500/scoreboard/gsw.png"),
            "Celtics": ("1610612738", "https://a.espncdn.com/i/teamlogos/nba/500/scoreboard/bos.png"),
        },
        "Baseball": {
            "Yankees": ("147", "https://a.espncdn.com/i/teamlogos/mlb/500/scoreboard/nyy.png"),
            "Dodgers": ("119", "https://a.espncdn.com/i/teamlogos/mlb/500/scoreboard/lad.png"),
        },
        "Hockey": {
            "Rangers": ("166", "https://a.espncdn.com/i/teamlogos/nhl/500/scoreboard/nyr.png"),
            "Bruins": ("130", "https://a.espncdn.com/i/teamlogos/nhl/500/scoreboard/bos.png"),
        },
    }

    # League logos
    LEAGUE_LOGOS = {
        "Football": "https://a.espncdn.com/i/teamlogos/soccer/500/_default.png",
        "Basketball": "https://a.espncdn.com/i/teamlogos/nba/500/_default.png",
        "Baseball": "https://a.espncdn.com/i/teamlogos/mlb/500/_default.png",
        "Hockey": "https://a.espncdn.com/i/teamlogos/nhl/500/_default.png",
        "Motor Sport": "https://cdn-icons-png.flaticon.com/512/4539/4539830.png",
        "Fight MMA": "https://streamcenter.xyz/mma.png",
        "Boxing": "https://cdn-icons-png.flaticon.com/512/2736/2736123.png",
        "WWE": "https://streamcenter.xyz/wwe.png",
        "Tennis": "https://cdn-icons-png.flaticon.com/512/3069/3069185.png",
    }

    def get_tvg_info(self, sport: str, event: str) -> tuple:
        """Get TVG ID and league logo for a sport/event."""
        tvg_id = f"{sport}.{event[:20].replace(' ', '.')}"
        league_logo = self.LEAGUE_LOGOS.get(sport, "")
        return (tvg_id, league_logo)


# Create global instances
network = Network()
leagues = Leagues()
