"""Logo thật của token và sàn, lấy từ CoinGecko (lưu đệm trong data/logos)."""
import os, io, json, logging, requests
from PIL import Image
from .market import SYM2ID, CG

log = logging.getLogger("logos")
EXCHANGES = {"BINANCE": "binance", "COINBASE": "gdax", "OKX": "okex", "BYBIT": "bybit_spot", "KRAKEN": "kraken", "BITGET": "bitget",
             "KUCOIN": "kucoin", "GATE": "gate", "HTX": "huobi", "MEXC": "mxc", "UPBIT": "upbit", "HYPERLIQUID": "hyperliquid"}
EXTRA_COINS = {"PEPE": "pepe", "SHIB": "shiba-inu", "WLD": "worldcoin-wld", "ENA": "ethena", "TAO": "bittensor", "APT": "aptos",
               "NEAR": "near", "DOT": "polkadot", "LTC": "litecoin", "BCH": "bitcoin-cash", "UNI": "uniswap", "AAVE": "aave",
               "MKR": "maker", "PAXG": "pax-gold", "XAUT": "tether-gold", "FDUSD": "first-digital-usd", "DAI": "dai", "USDE": "ethena-usde"}

class Logos:
    def __init__(self, root, key=None):
        self.dir = os.path.join(root, "data", "logos"); os.makedirs(self.dir, exist_ok=True); self.key = key; self.mem = {}
    def _h(self): return {"accept": "application/json", **({"x-cg-demo-api-key": self.key} if self.key else {})}

    def _download(self, url, path):
        r = requests.get(url, timeout=20); r.raise_for_status()
        im = Image.open(io.BytesIO(r.content)).convert("RGBA"); im.thumbnail((256, 256)); im.save(path); return im

    def get(self, name):
        """name: 'BTC' | 'USDT' | 'BINANCE' ... -> RGBA hoặc None"""
        k = str(name).upper().strip()
        if k in self.mem: return self.mem[k]
        path = os.path.join(self.dir, k + ".png"); im = None
        try:
            if os.path.exists(path): im = Image.open(path).convert("RGBA")
            elif k in EXCHANGES:
                js = requests.get(f"{CG}/exchanges/{EXCHANGES[k]}", headers=self._h(), timeout=20).json()
                if js.get("image"): im = self._download(js["image"], path)
            else:
                cid = SYM2ID.get(k) or EXTRA_COINS.get(k)
                if not cid:
                    res = requests.get(f"{CG}/search", params={"query": k}, headers=self._h(), timeout=20).json().get("coins", [])
                    cid = next((c["id"] for c in res if c.get("symbol", "").upper() == k), None)
                if cid:
                    js = requests.get(f"{CG}/coins/markets", params={"vs_currency": "usd", "ids": cid}, headers=self._h(), timeout=20).json()
                    if js and js[0].get("image"): im = self._download(js[0]["image"].replace("/small/", "/large/"), path)
        except Exception as e: log.warning("logo %s lỗi: %s", k, e)
        self.mem[k] = im; return im

def collect_names(script):
    """quét kịch bản lấy mọi ký hiệu token / tên sàn cần logo"""
    out = set()
    def walk(x, key=None):
        if isinstance(x, dict):
            for kk, vv in x.items(): walk(vv, kk)
        elif isinstance(x, list):
            for vv in x: walk(vv, key)
        elif isinstance(x, str) and key in ("token", "tokens", "sym", "symbol", "logo"):
            if 1 < len(x) <= 12 and not x.startswith("+"): out.add(x.upper())
    walk(script.get("beats", [])); return out
