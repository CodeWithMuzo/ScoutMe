import os
import time
import hashlib
import requests
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from bs4 import BeautifulSoup

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "raw_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

class KTFFClient:
    def __init__(self, use_cache=True, cache_dir=CACHE_DIR, delay_seconds=0.4):
        self.use_cache = use_cache
        self.cache_dir = cache_dir
        self.delay_seconds = delay_seconds
        self.session = requests.Session()
        
        # Setup retries
        retries = Retry(
            total=4,
            backoff_factor=1.0,
            status_forcelist=[429, 500, 502, 503, 504],
            raise_on_status=False
        )
        adapter = HTTPAdapter(max_retries=retries)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
            "Connection": "keep-alive"
        })

    def _get_cache_path(self, url):
        url_hash = hashlib.md5(url.encode("utf-8")).hexdigest()
        # Clean slug from url for easier inspection
        slug = url.split("?")[0].rstrip("/").split("/")[-1][:30]
        safe_slug = "".join([c if c.isalnum() or c in "-_" else "_" for c in slug])
        return os.path.join(self.cache_dir, f"{safe_slug}_{url_hash}.html")

    def get_html(self, url, timeout=35, force_refresh=False):
        cache_path = self._get_cache_path(url)
        
        if self.use_cache and not force_refresh and os.path.exists(cache_path):
            with open(cache_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()

        time.sleep(self.delay_seconds)
        
        try:
            resp = self.session.get(url, timeout=timeout)
            if resp.status_code == 200:
                html = resp.text
                if self.use_cache:
                    with open(cache_path, "w", encoding="utf-8") as f:
                        f.write(html)
                return html
            else:
                print(f"[WARN] HTTP {resp.status_code} for URL: {url}")
                return None
        except Exception as e:
            print(f"[ERROR] Fetching {url}: {e}")
            return None

    def get_soup(self, url, timeout=35, force_refresh=False):
        html = self.get_html(url, timeout=timeout, force_refresh=force_refresh)
        if html:
            return BeautifulSoup(html, "html.parser")
        return None
