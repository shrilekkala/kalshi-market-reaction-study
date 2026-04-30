import pandas as pd

# Convert Kalshi string numeric values to floats
def _to_number(value):
    return pd.to_numeric(value, errors="coerce")

# Safely extract a nested numeric value from a Kalshi candlestick
def _nested_number(row: dict, outer_key: str, inner_key: str):
    return _to_number(row.get(outer_key, {}).get(inner_key))


# Flatten Kalshi candlestick JSON into a dataframe for analysis.
def candlesticks_to_dataframe(candlesticks: list[dict]) -> pd.DataFrame:
    records = []

    for candle in candlesticks:
        record = {
            "timestamp_utc": pd.to_datetime(
                candle.get("end_period_ts"),
                unit="s",
                utc=True,
            ),
            "open_interest": _to_number(candle.get("open_interest_fp")),
            "volume": _to_number(candle.get("volume_fp")),

            # Actual traded price fields. These are only present when trades occurred.
            "trade_open": _nested_number(candle, "price", "open_dollars"),
            "trade_high": _nested_number(candle, "price", "high_dollars"),
            "trade_low": _nested_number(candle, "price", "low_dollars"),
            "trade_close": _nested_number(candle, "price", "close_dollars"),
            "trade_mean": _nested_number(candle, "price", "mean_dollars"),
            "trade_previous": _nested_number(candle, "price", "previous_dollars"),

            # Quote fields. These are useful even when no trade occurred.
            "yes_bid_close": _nested_number(candle, "yes_bid", "close_dollars"),
            "yes_ask_close": _nested_number(candle, "yes_ask", "close_dollars"),
        }

        records.append(record)

    df = pd.DataFrame(records)

    if df.empty:
        return df

    df["timestamp_et"] = df["timestamp_utc"].dt.tz_convert("America/New_York")

    # Midpoint gives a continuous market-implied price estimate from quotes.
    df["midpoint"] = (df["yes_bid_close"] + df["yes_ask_close"]) / 2

    # Spread measures the gap between buying and selling immediately.
    df["spread"] = df["yes_ask_close"] - df["yes_bid_close"]

    # Filled trade close is useful for plotting actual traded price when sparse.
    df["trade_close_filled"] = (
        df["trade_close"]
        .fillna(df["trade_previous"])
        .ffill()
    )

    return df


# Compute before/after price, volume, and spread metrics around an event.
def compute_reaction_metrics(
    candles_df: pd.DataFrame,
    event_time,
    window_hours: int,
) -> pd.DataFrame:
    if candles_df.empty:
        return pd.DataFrame()

    window = pd.Timedelta(hours=window_hours)

    before = candles_df[
        (candles_df["timestamp_et"] >= event_time - window)
        & (candles_df["timestamp_et"] < event_time)
    ]

    after = candles_df[
        (candles_df["timestamp_et"] >= event_time)
        & (candles_df["timestamp_et"] <= event_time + window)
    ]

    def first_valid(series):
        values = series.dropna()
        return values.iloc[0] if not values.empty else None

    def last_valid(series):
        values = series.dropna()
        return values.iloc[-1] if not values.empty else None

    price_before_start = first_valid(before["midpoint"])
    price_just_before = last_valid(before["midpoint"])
    price_just_after = first_valid(after["midpoint"])
    price_after_end = last_valid(after["midpoint"])

    volume_before = before["volume"].sum()
    volume_after = after["volume"].sum()

    avg_spread_before = before["spread"].mean()
    avg_spread_after = after["spread"].mean()

    metrics = {
        "event_time_et": event_time.isoformat(),
        "window_hours": window_hours,

        "price_2h_before_start_cents": price_before_start * 100 if price_before_start is not None else None,
        "price_just_before_cents": price_just_before * 100 if price_just_before is not None else None,
        "price_just_after_cents": price_just_after * 100 if price_just_after is not None else None,
        "price_2h_after_end_cents": price_after_end * 100 if price_after_end is not None else None,

        "pre_event_move_cents": (
            (price_just_before - price_before_start) * 100
            if price_before_start is not None and price_just_before is not None
            else None
        ),
        "post_event_move_cents": (
            (price_after_end - price_just_after) * 100
            if price_just_after is not None and price_after_end is not None
            else None
        ),

        "volume_before": volume_before,
        "volume_after": volume_after,
        "volume_ratio_after_before": (
            volume_after / volume_before if volume_before else None
        ),

        "avg_spread_before_cents": avg_spread_before * 100,
        "avg_spread_after_cents": avg_spread_after * 100,
    }

    return pd.DataFrame([metrics])