import requests

# Small wrapper around the public Kalshi market data API.
class KalshiClient:
    def __init__(self, base_url: str):
        # remove trailing slash
        self.base_url = base_url.rstrip("/")

    # Fetch metadata for a specific market
    def get_market(self, ticker: str) -> dict:
        url = f"{self.base_url}/markets/{ticker}"
        response = requests.get(url, timeout=30)
        # raises error if request fails
        response.raise_for_status()
        return response.json()["market"]

    # Fetch candlesticks for a market over a time window.
    def get_candlesticks(
        self,
        series_ticker: str,
        ticker: str,
        start_time,
        end_time,
        period_interval: int = 1,
    ) -> list[dict]:
        url = f"{self.base_url}/series/{series_ticker}/markets/{ticker}/candlesticks"

        params = {
            # convert times to Unix timestamps as Kalshi expects
            "start_ts": int(start_time.timestamp()),
            "end_ts": int(end_time.timestamp()),
            # interval 1 returns 1 minute candlesticks
            "period_interval": period_interval,
        }

        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()["candlesticks"]

    # Fetch the current order book for a market.
    def get_orderbook(self, ticker: str) -> dict:
        url = f"{self.base_url}/markets/{ticker}/orderbook"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()["orderbook_fp"]