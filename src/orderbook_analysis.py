import pandas as pd

# Parse one side of Kalshi's order book into a dataframe.
def parse_book_side(levels: list[list[str]], side: str) -> pd.DataFrame:
    df = pd.DataFrame(levels, columns=["price", "contracts"])

    if df.empty:
        return pd.DataFrame(columns=["price", "contracts", "side"])

    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df["contracts"] = pd.to_numeric(df["contracts"], errors="coerce")
    df["side"] = side

    return df

# Parse Kalshi YES/NO bid books and build implied YES asks.
def parse_orderbook(orderbook: dict) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Kalshi's orderbook endpoint returns YES bids and NO bids.
    Since YES and NO are complementary, a NO bid implies a YES ask: implied YES ask = 1 - NO bid
    """
    yes_bids = parse_book_side(orderbook.get("yes_dollars", []), "yes_bid")
    no_bids = parse_book_side(orderbook.get("no_dollars", []), "no_bid")

    yes_bids = yes_bids.sort_values("price", ascending=False).reset_index(drop=True)
    no_bids = no_bids.sort_values("price", ascending=False).reset_index(drop=True)

    yes_asks = no_bids.copy()
    yes_asks["price"] = 1 - yes_asks["price"]
    yes_asks["side"] = "yes_ask_implied"
    yes_asks = yes_asks.sort_values("price", ascending=True).reset_index(drop=True)

    return yes_bids, no_bids, yes_asks


# Compute top-of-book bid/ask, spread, midpoint, and depth metrics
def compute_liquidity_metrics(
    yes_bids: pd.DataFrame,
    yes_asks: pd.DataFrame,
) -> pd.DataFrame:
    if yes_bids.empty or yes_asks.empty:
        return pd.DataFrame()

    best_bid = yes_bids.iloc[0]
    best_ask = yes_asks.iloc[0]

    best_yes_bid = best_bid["price"]
    best_yes_ask = best_ask["price"]

    spread = best_yes_ask - best_yes_bid
    midpoint = (best_yes_bid + best_yes_ask) / 2

    metrics = {
        "best_yes_bid_cents": best_yes_bid * 100,
        "best_yes_bid_size": best_bid["contracts"],
        "implied_yes_ask_cents": best_yes_ask * 100,
        "implied_yes_ask_size": best_ask["contracts"],
        "spread_cents": spread * 100,
        "midpoint_cents": midpoint * 100,
        "total_yes_bid_depth": yes_bids["contracts"].sum(),
        "total_implied_yes_ask_depth": yes_asks["contracts"].sum(),
        "yes_bid_levels": len(yes_bids),
        "implied_yes_ask_levels": len(yes_asks),
    }

    return pd.DataFrame([metrics])


# Add cumulative depth columns for plotting.
def add_depth_columns(yes_bids: pd.DataFrame, yes_asks: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    bids_depth = yes_bids.copy()
    asks_depth = yes_asks.copy()

    # Bids are already sorted high to low; cumulative contracts from best bid downward.
    bids_depth["cum_contracts"] = bids_depth["contracts"].cumsum()
    bids_depth["price_cents"] = bids_depth["price"] * 100

    # Asks are already sorted low to high; cumulative contracts from best ask upward.
    asks_depth["cum_contracts"] = asks_depth["contracts"].cumsum()
    asks_depth["price_cents"] = asks_depth["price"] * 100

    return bids_depth, asks_depth


# Simulate buying YES by walking the implied YES ask book.
def simulate_buy_yes(yes_asks: pd.DataFrame, quantity: float) -> dict:
    """
    The buy order consumes the cheapest asks first. If there is not enough depth,
    the order is partially filled.
    """
    remaining = quantity
    total_cost = 0.0
    filled = 0.0
    fills = []

    for _, row in yes_asks.sort_values("price", ascending=True).iterrows():
        if remaining <= 0:
            break

        fill_qty = min(remaining, row["contracts"])
        fill_price = row["price"]

        fills.append(
            {
                "price": fill_price,
                "contracts": fill_qty,
                "cost": fill_qty * fill_price,
            }
        )

        total_cost += fill_qty * fill_price
        filled += fill_qty
        remaining -= fill_qty

    avg_price = total_cost / filled if filled > 0 else None
    worst_price = fills[-1]["price"] if fills else None

    return {
        "target_quantity": quantity,
        "filled_quantity": filled,
        "unfilled_quantity": remaining,
        "avg_price_cents": avg_price * 100 if avg_price is not None else None,
        "worst_price_cents": worst_price * 100 if worst_price is not None else None,
        "total_cost_dollars": total_cost,
    }


# Simulate buy-side slippage for multiple order sizes.
def simulate_slippage_curve(
    yes_asks: pd.DataFrame,
    quantities: list[float],
) -> pd.DataFrame:
    if yes_asks.empty:
        return pd.DataFrame()

    best_ask_cents = yes_asks.iloc[0]["price"] * 100

    rows = []
    for quantity in quantities:
        result = simulate_buy_yes(yes_asks, quantity)
        result["best_ask_cents"] = best_ask_cents
        result["slippage_vs_best_ask_cents"] = (
            result["avg_price_cents"] - best_ask_cents
            if result["avg_price_cents"] is not None
            else None
        )
        rows.append(result)

    return pd.DataFrame(rows)