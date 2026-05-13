import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import aiohttp
from pathlib import Path

# Logger Setup
def get_logger(name):
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    return logging.getLogger(name)

# Cache System
class Cache:
    def __init__(self, tag, exp=86400):
        self.tag = tag
        self.exp = exp
        self.file = Path(f"{tag.lower()}_cache.json")

    def load(self):
        if self.file.exists():
            try:
                with open(self.file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def write(self, data):
        with open(self.file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

# Time Management
class Time:
    @staticmethod
    def now():
        return datetime.now(timezone.utc)
    
    @staticmethod
    def clean(dt_obj):
        return dt_obj
    
    @staticmethod
    def from_str(time_str, timezone="CET"):
        try:
            dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
            return dt.astimezone(ZoneInfo(timezone))
        except ValueError:
            return datetime.now(ZoneInfo(timezone))

# Leagues & TVG Info
class leagues:
    @staticmethod
    def get_tvg_info(sport, event):
        tvg_id = f"{sport.replace(' ', '')}.us"
        logo_url = "" 
        return (tvg_id, logo_url)

# Async Network Engine
class NetworkResponse:
    def __init__(self, content, json_data):
        self.content = content
        self._json = json_data

    def json(self):
        return self._json

class network:
    HTTP_S = asyncio.Semaphore(10)

    @staticmethod
    async def request(url, params=None, log=None):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=15) as response:
                    content = await response.text()
                    try:
                        json_data = await response.json(content_type=None)
                    except Exception:
                        json_data = None
                        
                    if response.status == 200:
                        return NetworkResponse(content, json_data)
        except Exception as e:
            if log:
                log.warning(f"Request failed for {url}: {e}")
        return None

    @staticmethod
    async def safe_process(handler, url_num, semaphore, log):
        async with semaphore:
            try:
                return await handler()
            except Exception as e:
                if log:
                    log.warning(f"Error processing URL {url_num}: {e}")
                return None
