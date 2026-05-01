import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter

from zoneinfo import ZoneInfo
import pandas as pd

# Filter candlestick dataframe to the configured plot window
def _filter_plot_window(candles_df: pd.DataFrame, start_time, end_time) -> pd.DataFrame:
    if candles_df.empty:
        return candles_df

    return candles_df[
        (candles_df["timestamp_et"] >= start_time)
        & (candles_df["timestamp_et"] <= end_time)
    ].copy()

# Format large y-axis values like 10000 as 10k
def _format_thousands(x, _):
    if abs(x) >= 1000:
        return f"{x / 1000:.0f}k"
    return f"{x:.0f}"

# Format price values as cents
def _format_cents(x, _):
    return f"{x:.1f}¢"

# Apply consistent styling to plots
def _apply_common_style(ax, include_x_grid: bool = False):
    ax.grid(True, axis="y", alpha=0.3)

    if include_x_grid:
        ax.grid(True, axis="x", alpha=0.18)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

# Plot YES midpoint price around the event timestamp
def plot_price_reaction(
    candles_df: pd.DataFrame,
    event_time,
    start_time,
    end_time,
    output_path,
    press_conference_time=None,
) -> None:
    plot_df = _filter_plot_window(candles_df, start_time, end_time)

    if plot_df.empty:
        print(f"Skipping price plot; no candlestick data available for {output_path}")
        return

    fig, ax = plt.subplots(figsize=(12, 6))

    ax.plot(
        plot_df["timestamp_et"],
        plot_df["midpoint"] * 100,
        linewidth=2,
        label="YES bid/ask midpoint",
    )

    ax.axvline(
        event_time,
        color="black",
        linestyle="--",
        linewidth=2,
        alpha=0.8,
        label="Fed decision timestamp",
    )

    if press_conference_time is not None:
        ax.axvline(
            press_conference_time,
            color="gray",
            linestyle=":",
            linewidth=2,
            alpha=0.9,
            label="Press conference begins",
    )

    ax.set_xlabel("Time (ET)")
    ax.set_ylabel("YES midpoint price")
    ax.set_title('YES Midpoint for "0 Cuts in 2026" Around Fed Decision')
    ax.yaxis.set_major_formatter(FuncFormatter(_format_cents))
    ax.legend()
    ax.tick_params(axis="x", rotation=0)
    formatter = mdates.DateFormatter("%b %d\n%H:%M")
    formatter.set_tzinfo(ZoneInfo("America/New_York"))
    ax.xaxis.set_major_formatter(formatter)
    _apply_common_style(ax, include_x_grid=True)

    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)

# Plot traded volume around the event timestamp, aggregated into time buckets
def plot_volume_reaction(
    candles_df: pd.DataFrame,
    event_time,
    start_time,
    end_time,
    output_path,
    bucket_size: str = "15min",
    press_conference_time=None,
) -> None:
    plot_df = _filter_plot_window(candles_df, start_time, end_time)

    if plot_df.empty:
        print(f"Skipping volume plot; no candlestick data available for {output_path}")
        return

    volume_df = (
        plot_df
        .set_index("timestamp_et")
        .resample(bucket_size)["volume"]
        .sum()
        .reset_index()
    )

    if bucket_size == "15min":
        bar_width = 10 / (24 * 60)  # 10 minutes, in matplotlib date units
    else:
        bar_width = 0.003

    fig, ax = plt.subplots(figsize=(12, 6))

    ax.bar(
        volume_df["timestamp_et"],
        volume_df["volume"],
        width=bar_width,
        label=f"Contracts traded ({bucket_size} buckets)",
    )

    ax.axvline(
        event_time,
        color="black",
        linestyle="--",
        linewidth=2,
        alpha=0.8,
        label="Fed decision timestamp",
    )

    if press_conference_time is not None:
        ax.axvline(
            press_conference_time,
            color="gray",
            linestyle=":",
            linewidth=2,
            alpha=0.9,
            label="Press conference begins",
    )

    ax.set_xlabel("Time (ET)")
    ax.set_ylabel("Contracts traded")
    ax.set_title("Trading Volume Around Fed Decision")
    ax.yaxis.set_major_formatter(FuncFormatter(_format_thousands))
    ax.legend()
    ax.tick_params(axis="x", rotation=0)
    formatter = mdates.DateFormatter("%b %d\n%H:%M")
    formatter.set_tzinfo(ZoneInfo("America/New_York"))
    ax.xaxis.set_major_formatter(formatter)
    _apply_common_style(ax, include_x_grid=True)

    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)

# Plot cumulative YES bid and implied YES ask depth
def plot_orderbook_depth(
    bids_depth: pd.DataFrame,
    asks_depth: pd.DataFrame,
    output_path,
    focus_top_of_book: bool = True,
) -> None:
    if bids_depth.empty and asks_depth.empty:
        print(f"Skipping order book depth plot; no data available for {output_path}")
        return

    plot_bids = bids_depth.copy()
    plot_asks = asks_depth.copy()

    if focus_top_of_book and not bids_depth.empty and not asks_depth.empty:
        best_bid = bids_depth["price_cents"].max()
        best_ask = asks_depth["price_cents"].min()

        lower_bound = max(0, best_bid - 8)
        upper_bound = min(100, best_ask + 12)

        plot_bids = plot_bids[
            (plot_bids["price_cents"] >= lower_bound)
            & (plot_bids["price_cents"] <= upper_bound)
        ]

        plot_asks = plot_asks[
            (plot_asks["price_cents"] >= lower_bound)
            & (plot_asks["price_cents"] <= upper_bound)
        ]

    fig, ax = plt.subplots(figsize=(10, 6))

    if not plot_bids.empty:
        ax.step(
            plot_bids["price_cents"],
            plot_bids["cum_contracts"],
            where="post",
            linewidth=2,
            label="YES bids",
        )

    if not plot_asks.empty:
        ax.step(
            plot_asks["price_cents"],
            plot_asks["cum_contracts"],
            where="post",
            linewidth=2,
            label="Implied YES asks",
        )

    ax.set_xlabel("YES price")
    ax.set_ylabel("Cumulative contracts")
    ax.set_title("Current Order Book Depth Near Top of Book")
    ax.xaxis.set_major_formatter(FuncFormatter(_format_cents))
    ax.yaxis.set_major_formatter(FuncFormatter(_format_thousands))
    ax.legend()
    _apply_common_style(ax)

    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)

# Plot simulated buy-side slippage by order size
def plot_slippage_curve(
    slippage_df: pd.DataFrame,
    output_path,
) -> None:
    if slippage_df.empty:
        print(f"Skipping slippage plot; no data available for {output_path}")
        return

    fig, ax = plt.subplots(figsize=(10, 6))

    ax.plot(
        slippage_df["target_quantity"],
        slippage_df["slippage_vs_best_ask_cents"],
        marker="o",
        linewidth=2,
    )

    ax.set_xlabel("Buy order size (YES contracts)")
    ax.set_ylabel("Slippage vs best ask")
    ax.set_title('Simulated Buy-Side Slippage for "0 Cuts in 2026"')
    ax.xaxis.set_major_formatter(FuncFormatter(_format_thousands))
    ax.yaxis.set_major_formatter(FuncFormatter(_format_cents))
    _apply_common_style(ax)

    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)