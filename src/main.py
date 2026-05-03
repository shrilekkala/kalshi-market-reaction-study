import pandas as pd

from src.config import (
    BASE_URL,
    SERIES_TICKER,
    EVENT_TICKER,
    MARKET_TICKER,
    MARKET_DESCRIPTION,
    EVENT_TIME,
    PRESS_CONFERENCE_TIME,
    START_TIME,
    END_TIME,
    REACTION_WINDOW_HOURS,
    OUTPUT_DIR,
    ENVIRONMENT_NAME,
)

from src.kalshi_client import KalshiClient

from src.market_activity import (
    candlesticks_to_dataframe,
    compute_reaction_metrics,
)

from src.orderbook_analysis import (
    parse_orderbook,
    compute_liquidity_metrics,
    add_depth_columns,
    simulate_slippage_curve,
)

from src.plots import (
    plot_price_reaction,
    plot_volume_reaction,
    plot_orderbook_depth,
    plot_slippage_curve,
)

def print_section(title: str) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)

def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print_section("Kalshi Market Reaction and Liquidity Study")
    print(f"Environment: {ENVIRONMENT_NAME}")
    print(f"Base URL: {BASE_URL}")
    print(f"Series: {SERIES_TICKER}")
    print(f"Event: {EVENT_TICKER}")
    print(f"Market: {MARKET_TICKER}")
    print(f"Description: {MARKET_DESCRIPTION}")
    print(f"Output directory: {OUTPUT_DIR}")

    client = KalshiClient(BASE_URL)

    print_section("Fetching market metadata")
    market = client.get_market(MARKET_TICKER)

    market_summary = {
        "ticker": market.get("ticker"),
        "title": market.get("title"),
        "subtitle": market.get("subtitle"),
        "status": market.get("status"),
        "last_price_dollars": market.get("last_price_dollars"),
        "yes_bid_dollars": market.get("yes_bid_dollars"),
        "yes_ask_dollars": market.get("yes_ask_dollars"),
        "no_bid_dollars": market.get("no_bid_dollars"),
        "no_ask_dollars": market.get("no_ask_dollars"),
        "volume_fp": market.get("volume_fp"),
        "volume_24h_fp": market.get("volume_24h_fp"),
        "open_interest_fp": market.get("open_interest_fp"),
        "close_time": market.get("close_time"),
        "rules_primary": market.get("rules_primary"),
    }

    market_summary_df = pd.DataFrame([market_summary])
    market_summary_df.to_csv(OUTPUT_DIR / "market_summary.csv", index=False)

    print(market_summary_df.T)

    print_section("Fetching candlesticks")
    candlesticks = client.get_candlesticks(
        SERIES_TICKER,
        MARKET_TICKER,
        START_TIME,
        END_TIME,
        period_interval=1,
    )

    candles_df = candlesticks_to_dataframe(candlesticks)
    candles_df.to_csv(OUTPUT_DIR / "candlesticks.csv", index=False)

    print(f"Candlesticks returned: {len(candles_df)}")

    reaction_metrics = compute_reaction_metrics(
        candles_df,
        EVENT_TIME,
        REACTION_WINDOW_HOURS,
    )
    reaction_metrics.to_csv(OUTPUT_DIR / "reaction_metrics.csv", index=False)

    print_section("Reaction metrics")
    if reaction_metrics.empty:
        print("No reaction metrics available.")
    else:
        print(reaction_metrics.T)

    print_section("Fetching order book")
    orderbook = client.get_orderbook(MARKET_TICKER)

    yes_bids, no_bids, yes_asks = parse_orderbook(orderbook)
    yes_bids.to_csv(OUTPUT_DIR / "yes_bids.csv", index=False)
    no_bids.to_csv(OUTPUT_DIR / "no_bids.csv", index=False)
    yes_asks.to_csv(OUTPUT_DIR / "implied_yes_asks.csv", index=False)

    print(f"YES bid levels: {len(yes_bids)}")
    print(f"NO bid levels: {len(no_bids)}")
    print(f"Implied YES ask levels: {len(yes_asks)}")

    liquidity_metrics = compute_liquidity_metrics(yes_bids, yes_asks)
    liquidity_metrics.to_csv(OUTPUT_DIR / "liquidity_metrics.csv", index=False)

    print_section("Liquidity metrics")
    if liquidity_metrics.empty:
        print("No liquidity metrics available.")
    else:
        print(liquidity_metrics.T)

    bids_depth, asks_depth = add_depth_columns(yes_bids, yes_asks)
    bids_depth.to_csv(OUTPUT_DIR / "yes_bid_depth.csv", index=False)
    asks_depth.to_csv(OUTPUT_DIR / "implied_yes_ask_depth.csv", index=False)

    slippage_df = simulate_slippage_curve(
        yes_asks,
        quantities=[10, 100, 500, 1000, 5000, 10000],
    )
    slippage_df.to_csv(OUTPUT_DIR / "slippage_simulation.csv", index=False)

    print_section("Slippage simulation")
    if slippage_df.empty:
        print("No slippage simulation available.")
    else:
        print(slippage_df)

    print_section("Generating plots")
    plot_price_reaction(
        candles_df,
        EVENT_TIME,
        START_TIME,
        END_TIME,
        OUTPUT_DIR / "price_reaction.png",
        press_conference_time=PRESS_CONFERENCE_TIME,
    )

    plot_volume_reaction(
        candles_df,
        EVENT_TIME,
        START_TIME,
        END_TIME,
        OUTPUT_DIR / "volume_reaction.png",
        press_conference_time=PRESS_CONFERENCE_TIME,
    )

    plot_orderbook_depth(
        bids_depth,
        asks_depth,
        OUTPUT_DIR / "orderbook_depth.png",
    )

    plot_slippage_curve(
        slippage_df,
        OUTPUT_DIR / "slippage_by_size.png",
    )

    for plot_name in [
        "price_reaction.png",
        "volume_reaction.png",
        "orderbook_depth.png",
        "slippage_by_size.png",
    ]:
        print(OUTPUT_DIR / plot_name)

    print_section("Done")
    print(f"Saved outputs to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()