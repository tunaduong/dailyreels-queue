"""Dữ liệu thị trường thật: giá/biến động 24h (CoinGecko), nến OHLC, chỉ số Sợ hãi & Tham lam (alternative.me)."""
import logging, requests
from .render.core import fmt_price

log = logging.getLogger("market")
CG = "https://api.coingecko.com/api/v3"
SYM2ID = {"BTC": "bitcoin", "ETH": "ethereum", "BNB": "binancecoin", "SOL": "solana", "XRP": "ripple", "TRX": "tron",
          "DOGE": "dogecoin", "TON": "the-open-network", "ADA": "cardano", "AVAX": "avalanche-2", "LINK": "chainlink",
          "HYPE": "hyperliquid", "SUI": "sui", "ARB": "arbitrum", "OP": "optimism", "USDT": "tether", "USDC": "usd-coin"}

def _get(url, params=None, key=None, tries=4):
    """gọi CoinGecko, tự chờ và thử lại khi bị giới hạn (429)"""
    import time
    h = {"accept": "application/json"}
    if key: h["x-cg-demo-api-key"] = key
    for i in range(tries):
        r = requests.get(url, params=params, headers=h, timeout=25)
        if r.status_code == 429 and i < tries - 1:
            wait = int(r.headers.get("Retry-After") or 0) or 15 * (i + 1); log.info("CoinGecko 429, chờ %ss", wait); time.sleep(min(wait, 60)); continue
        r.raise_for_status(); return r.json()

def ticker(symbols, key=None):
    """-> [(SYM, '76.974', -5.02), ...] ; rỗng nếu lỗi"""
    try:
        ids = [SYM2ID.get(s.upper(), s.lower()) for s in symbols]
        js = _get(f"{CG}/simple/price", {"ids": ",".join(ids), "vs_currencies": "usd", "include_24hr_change": "true"}, key)
        out = []
        for s, i in zip(symbols, ids):
            if i in js and "usd" in js[i]: out.append((s.upper(), fmt_price(js[i]["usd"]), float(js[i].get("usd_24h_change") or 0)))
        return out
    except Exception as e:
        log.warning("ticker lỗi: %s", e); return []

def ohlc(symbol_or_id, days=1, key=None):
    """-> [(o,h,l,c,vol)] thật từ CoinGecko; None nếu lỗi. CoinGecko OHLC không có volume => dùng biên độ nến làm cột phụ."""
    try:
        cid = SYM2ID.get(str(symbol_or_id).upper(), str(symbol_or_id).lower())
        js = _get(f"{CG}/coins/{cid}/ohlc", {"vs_currency": "usd", "days": days}, key)
        rows = [(float(o), float(h), float(l), float(c), float(h) - float(l)) for _, o, h, l, c in js]
        return rows[-60:] if rows else None
    except Exception as e:
        log.warning("ohlc lỗi: %s", e); return None

def fear_greed():
    try:
        js = requests.get("https://api.alternative.me/fng/", params={"limit": 2}, timeout=20).json()["data"]
        return {"now": int(js[0]["value"]), "prev": int(js[1]["value"])}
    except Exception as e:
        log.warning("fear&greed lỗi: %s", e); return None
