from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"

SERIES_TICKER = "KXRATECUTCOUNT"
EVENT_TICKER = "KXRATECUTCOUNT-26DEC31"
MARKET_TICKER = "KXRATECUTCOUNT-26DEC31-T0"

MARKET_DESCRIPTION = "Exactly 0 Fed rate cuts in 2026"

EASTERN = ZoneInfo("America/New_York")

# External event anchor: Fed decision timestamp.
# We use 2:00 PM ET as the expected FOMC statement/release time.
EVENT_TIME = datetime(2026, 4, 29, 14, 0, tzinfo=EASTERN)

# Broad window used for the chart/data pull.
START_TIME = datetime(2026, 4, 29, 9, 0, tzinfo=EASTERN)
END_TIME = datetime(2026, 4, 30, 9, 0, tzinfo=EASTERN)

# Before/after window used for summary metrics.
REACTION_WINDOW_HOURS = 2

OUTPUT_DIR = Path("outputs")