"""Batch runner + CSV exporter for fetch-data.py

Goal:
  - Keep your original fetch-data.py unchanged
  - Let you paste a comma-separated list of tickers
  - Analyze one by one (same console output style as fetch-data.py)
  - Save all key values into a single CSV file

Run:
  python3 fetch-data-batch.py

Notes:
  This file re-implements a compact version of the "snapshot + key ratios + health score"
  extraction using yfinance, and writes results to CSV.
"""

import warnings
from datetime import datetime
from pathlib import Path

import pandas as pd
import yfinance as yf


warnings.filterwarnings("ignore")


"""This batch script is intentionally *comparison-first*.

User request:
  - Remove the extra 5-year back information
  - Keep only important fields
  - Write comparison-friendly CSV
  - Also write a comparable TXT report that's easy to analyze

So we only keep a compact set of snapshot + key ratios + health metrics.
"""


def convert_to_crores(value):
    """Convert raw number to Indian Crores (same logic as fetch-data.py)."""
    if value is None:
        return "N/A"
    try:
        if pd.isna(value):
            return "N/A"
    except Exception:
        pass
    try:
        return round(float(value) / 1e7, 2)
    except Exception:
        return "N/A"


def get_safe(data: dict, key: str, default="N/A"):
    """Safely get a value from yfinance info dict."""
    try:
        val = data.get(key, default)
        if val is None:
            return "N/A"
        # pandas NaN
        try:
            if isinstance(val, float) and pd.isna(val):
                return "N/A"
        except Exception:
            pass
        return val
    except Exception:
        return "N/A"


def analyze_ticker_to_record(ticker_symbol: str) -> dict:
    """Fetch yfinance info and return a compact record suitable for *comparison*.

    Intentionally excludes multi-year statements to keep outputs small and easy
    to compare across many tickers.
    """
    ticker_symbol = ticker_symbol.strip().upper()
    stock = yf.Ticker(ticker_symbol)
    info = stock.info or {}

    # minimal validity check
    if not info or (info.get("regularMarketPrice") is None and info.get("currentPrice") is None):
        return {
            "ticker": ticker_symbol,
            "error": "No market price found (invalid ticker or data unavailable)",
        }

    company_name = get_safe(info, "longName", ticker_symbol)
    sector = get_safe(info, "sector")
    industry = get_safe(info, "industry")
    exchange = get_safe(info, "exchange")

    current_price = get_safe(info, "currentPrice")
    if current_price == "N/A":
        current_price = get_safe(info, "regularMarketPrice")

    record: dict = {
        "ticker": ticker_symbol,
        "company_name": company_name,
        "sector": sector,
        "industry": industry,
        "exchange": exchange,
        "current_price": current_price,
        "previous_close": get_safe(info, "previousClose"),
        "52w_high": get_safe(info, "fiftyTwoWeekHigh"),
        "52w_low": get_safe(info, "fiftyTwoWeekLow"),
        "market_cap": get_safe(info, "marketCap"),
        "currency": get_safe(info, "currency", "INR"),
        # Key ratios (same keys you show in fetch-data.py)
        "pe_ratio_trailing": get_safe(info, "trailingPE"),
        "pe_ratio_forward": get_safe(info, "forwardPE"),
        "pb_ratio": get_safe(info, "priceToBook"),
        "ps_ratio": get_safe(info, "priceToSalesTrailing12Months"),
        "peg_ratio": get_safe(info, "pegRatio"),
        "roe": get_safe(info, "returnOnEquity"),
        "roa": get_safe(info, "returnOnAssets"),
        "debt_to_equity": get_safe(info, "debtToEquity"),
        "current_ratio": get_safe(info, "currentRatio"),
        "quick_ratio": get_safe(info, "quickRatio"),
        "dividend_yield": get_safe(info, "dividendYield"),
        "beta": get_safe(info, "beta"),
        "eps_trailing": get_safe(info, "trailingEps"),
        "eps_forward": get_safe(info, "forwardEps"),
        "profit_margins": get_safe(info, "profitMargins"),
        "operating_margins": get_safe(info, "operatingMargins"),
        "gross_margins": get_safe(info, "grossMargins"),
        "revenue_growth": get_safe(info, "revenueGrowth"),
        "earnings_growth": get_safe(info, "earningsGrowth"),
        "error": "",
    }

    # --- Derived snapshot values (used in fetch-data.py display) ---
    try:
        cp = record["current_price"]
        high = record["52w_high"]
        low = record["52w_low"]
        record["pct_from_52w_high"] = round(((float(cp) - float(high)) / float(high)) * 100, 2)
        record["pct_from_52w_low"] = round(((float(cp) - float(low)) / float(low)) * 100, 2)
    except Exception:
        record["pct_from_52w_high"] = "N/A"
        record["pct_from_52w_low"] = "N/A"

    # --- FCF yield (best-effort) ---
    # Prefer yfinance info keys where available to avoid pulling full statements.
    fcf_yield = get_safe(info, "freeCashflow")
    try:
        mcap = info.get("marketCap")
        if fcf_yield not in ("N/A", None) and mcap:
            record["fcf_yield_latest_year_pct"] = round((float(fcf_yield) / float(mcap)) * 100, 2)
        else:
            record["fcf_yield_latest_year_pct"] = "N/A"
    except Exception:
        record["fcf_yield_latest_year_pct"] = "N/A"

    # Health score (same spirit as fetch-data.py)
    score = 0
    max_score = 0

    def _ok(cond):
        nonlocal score, max_score
        max_score += 1
        if cond:
            score += 1

    try:
        roe = record["roe"]
        _ok(roe != "N/A" and float(roe) >= 0.15)
    except Exception:
        _ok(False)

    try:
        de = record["debt_to_equity"]
        _ok(de != "N/A" and float(de) / 100 < 1.0)
    except Exception:
        _ok(False)

    try:
        pe = record["pe_ratio_trailing"]
        _ok(pe != "N/A" and float(pe) > 0)
    except Exception:
        _ok(False)

    try:
        pb = record["pb_ratio"]
        _ok(pb != "N/A" and float(pb) > 0)
    except Exception:
        _ok(False)

    try:
        cr = record["current_ratio"]
        _ok(cr != "N/A" and float(cr) >= 1.5)
    except Exception:
        _ok(False)

    record["health_score"] = score
    record["health_score_max"] = max_score
    return record


def pretty_print_company_report(record: dict):
    """Print a readable per-company report to the terminal.

    Kept intentionally compact (no multi-year statements).
    """
    ticker = record.get("ticker", "")
    print("\n" + "═" * 65)
    print(f"  REPORT: {ticker}")
    print("═" * 65)

    if record.get("error"):
        print(f"  ❌ ERROR: {record['error']}")
        return

    print(f"  Company  : {record.get('company_name','N/A')}")
    print(f"  Sector   : {record.get('sector','N/A')}")
    print(f"  Industry : {record.get('industry','N/A')}")
    print(f"  Exchange : {record.get('exchange','N/A')}")

    def _fmt(v, digits=2):
        if v in (None, "N/A", ""):
            return "N/A"
        try:
            if isinstance(v, str) and v.lower() == "nan":
                return "N/A"
            if pd.isna(v):
                return "N/A"
        except Exception:
            pass
        try:
            f = float(v)
            return f"{f:,.{digits}f}" if digits is not None else f"{f:,}"
        except Exception:
            return str(v)

    def _pct(v):
        if v in (None, "N/A", ""):
            return "N/A"
        try:
            if isinstance(v, str) and v.lower() == "nan":
                return "N/A"
            if pd.isna(v):
                return "N/A"
        except Exception:
            pass
        try:
            return f"{float(v):.2f}%"
        except Exception:
            return "N/A"

    print("\n  CURRENT MARKET SNAPSHOT")
    print("  " + "-" * 61)
    print(f"  Current Price   : {_fmt(record.get('current_price'))}")
    print(f"  Previous Close  : {_fmt(record.get('previous_close'))}")
    print(f"  52W High        : {_fmt(record.get('52w_high'))}  ({_pct(record.get('pct_from_52w_high'))} from High)")
    # note: pct_from_52w_low is already a positive number in our calculation
    print(f"  52W Low         : {_fmt(record.get('52w_low'))}  (+{_pct(record.get('pct_from_52w_low'))} from Low)")
    print(f"  Market Cap      : {_fmt(record.get('market_cap'), digits=None)}")
    print(f"  Currency        : {record.get('currency','N/A')}")

    print("\n  KEY RATIOS")
    print("  " + "-" * 61)
    print(f"  P/E (Trailing)  : {_fmt(record.get('pe_ratio_trailing'))}x")
    print(f"  P/E (Forward)   : {_fmt(record.get('pe_ratio_forward'))}x")
    print(f"  P/B             : {_fmt(record.get('pb_ratio'))}x")
    print(f"  P/S             : {_fmt(record.get('ps_ratio'))}x")
    print(f"  PEG             : {_fmt(record.get('peg_ratio'))}x")
    # ROE/ROA are fractions in yfinance (e.g. 0.32). Print as percent.
    roe = record.get('roe')
    roa = record.get('roa')
    try:
        roe = float(roe) * 100
    except Exception:
        pass
    try:
        roa = float(roa) * 100
    except Exception:
        pass
    print(f"  ROE             : {_pct(roe)}")
    print(f"  ROA             : {_pct(roa)}")
    print(f"  D/E             : {_fmt(record.get('debt_to_equity'))}")
    print(f"  Current Ratio   : {_fmt(record.get('current_ratio'))}x")
    print(f"  Quick Ratio     : {_fmt(record.get('quick_ratio'))}x")
    # dividend yield is fraction; print percent
    dy = record.get('dividend_yield')
    try:
        dy = float(dy) * 100
    except Exception:
        pass
    print(f"  Dividend Yield  : {_pct(dy)}")
    print(f"  Beta            : {_fmt(record.get('beta'))}")
    print(f"  EPS (Trailing)  : {_fmt(record.get('eps_trailing'))}")
    print(f"  EPS (Forward)   : {_fmt(record.get('eps_forward'))}")
    print(f"  FCF Yield (latest year) : {_pct(record.get('fcf_yield_latest_year_pct'))}")

    print("\n  HEALTH SCORE")
    print("  " + "-" * 61)
    print(f"  Score: {record.get('health_score','N/A')} / {record.get('health_score_max','N/A')}")


def _as_float_or_none(v):
    if v in (None, "N/A", ""):
        return None
    try:
        if isinstance(v, str) and v.lower() == "nan":
            return None
        if pd.isna(v):
            return None
    except Exception:
        pass
    try:
        return float(v)
    except Exception:
        return None


def _fmt_num(v, digits=2, suffix=""):
    f = _as_float_or_none(v)
    if f is None:
        return "N/A"
    if digits is None:
        return f"{f:,.0f}{suffix}"
    return f"{f:,.{digits}f}{suffix}"


def _fmt_pct_from_fraction(v):
    """yfinance margins/growth are often fractions (0.12 => 12%)."""
    f = _as_float_or_none(v)
    if f is None:
        return "N/A"
    return f"{f * 100:.2f}%"


def _write_comparison_txt(out_path: Path, records: list[dict]):
    """Write a compact, comparable TXT report (table-like)."""
    lines = []
    lines.append("=" * 120)
    lines.append("BATCH STOCK COMPARISON (compact)")
    lines.append("=" * 120)
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    ok = [r for r in records if not r.get("error")]
    bad = [r for r in records if r.get("error")]

    if bad:
        lines.append("FAILED TICKERS")
        lines.append("-" * 120)
        for r in bad:
            lines.append(f"{r.get('ticker',''):<15}  {r.get('error','')}")
        lines.append("")

    if not ok:
        lines.append("No successful tickers to compare.")
        out_path.write_text("\n".join(lines), encoding="utf-8")
        return

    # Stable column order for easy scanning.
    columns = [
        ("Ticker", lambda r: str(r.get("ticker", ""))),
        ("Price", lambda r: _fmt_num(r.get("current_price"), 2)),
        ("MCap", lambda r: _fmt_num(r.get("market_cap"), None)),
        ("52W%Hi", lambda r: _fmt_num(r.get("pct_from_52w_high"), 2, "%")),
        ("52W%Lo", lambda r: _fmt_num(r.get("pct_from_52w_low"), 2, "%")),
        ("PE", lambda r: _fmt_num(r.get("pe_ratio_trailing"), 2)),
        ("PB", lambda r: _fmt_num(r.get("pb_ratio"), 2)),
        ("ROE%", lambda r: _fmt_pct_from_fraction(r.get("roe"))),
        ("D/E%", lambda r: _fmt_num(r.get("debt_to_equity"), 1)),
        ("CR", lambda r: _fmt_num(r.get("current_ratio"), 2)),
        ("Div%", lambda r: _fmt_pct_from_fraction(r.get("dividend_yield"))),
        ("NetM%", lambda r: _fmt_pct_from_fraction(r.get("profit_margins"))),
        ("RevG%", lambda r: _fmt_pct_from_fraction(r.get("revenue_growth"))),
        ("EarnG%", lambda r: _fmt_pct_from_fraction(r.get("earnings_growth"))),
        ("FCFy%", lambda r: _fmt_num(r.get("fcf_yield_latest_year_pct"), 2, "%")),
        ("Score", lambda r: f"{r.get('health_score','')}/{r.get('health_score_max','')}"),
        ("Sector", lambda r: str(r.get("sector", ""))[:18]),
    ]

    # Determine column widths.
    col_names = [c[0] for c in columns]
    widths = []
    for name, fn in columns:
        w = len(name)
        for r in ok:
            try:
                w = max(w, len(str(fn(r))))
            except Exception:
                w = max(w, 3)
        widths.append(min(w, 28))

    def fmt_row(values):
        parts = []
        for v, w in zip(values, widths):
            s = str(v)
            if len(s) > w:
                s = s[: w - 1] + "…"
            parts.append(s.ljust(w))
        return "  ".join(parts)

    lines.append("COMPARISON TABLE")
    lines.append("-" * 120)
    lines.append(fmt_row(col_names))
    lines.append(fmt_row(["-" * min(w, 10) for w in widths]))
    for r in ok:
        lines.append(fmt_row([fn(r) for _, fn in columns]))

    lines.append("")
    lines.append("NOTES")
    lines.append("-" * 120)
    lines.append("- ROE%, Div%, NetM%, RevG%, EarnG% are shown as percentages.")
    lines.append("- D/E% is the yfinance Debt-to-Equity value (often already percent-like).")
    lines.append("- FCFy% is derived from freeCashflow/marketCap when available.")

    out_path.write_text("\n".join(lines), encoding="utf-8")


def make_readable_option_b(df: pd.DataFrame) -> pd.DataFrame:
    """Option B: reorder + shorten column names (non-destructive).

    Produces a second dataframe intended for humans.
    """
    cols = list(df.columns)
    snapshot = [
        "ticker",
        "company_name",
        "sector",
        "industry",
        "exchange",
        "currency",
        "current_price",
        "previous_close",
        "52w_high",
        "52w_low",
        "pct_from_52w_high",
        "pct_from_52w_low",
        "market_cap",
    ]
    ratios = [
        "pe_ratio_trailing",
        "pe_ratio_forward",
        "pb_ratio",
        "ps_ratio",
        "peg_ratio",
        "roe",
        "roa",
        "debt_to_equity",
        "current_ratio",
        "quick_ratio",
        "dividend_yield",
        "beta",
        "eps_trailing",
        "eps_forward",
    ]
    extra_compare = [
        "profit_margins",
        "operating_margins",
        "gross_margins",
        "revenue_growth",
        "earnings_growth",
    ]
    meta = ["fcf_yield_latest_year_pct", "health_score", "health_score_max", "error"]

    ordered = (
        [c for c in snapshot if c in cols]
        + [c for c in ratios if c in cols]
        + [c for c in extra_compare if c in cols]
        + [c for c in meta if c in cols]
    )

    rename = {
        "company_name": "name",
        "previous_close": "prev_close",
        "pct_from_52w_high": "from_52w_high_pct",
        "pct_from_52w_low": "from_52w_low_pct",
        "pe_ratio_trailing": "pe_ttm",
        "pe_ratio_forward": "pe_fwd",
        "pb_ratio": "pb",
        "ps_ratio": "ps",
        "peg_ratio": "peg",
        "debt_to_equity": "debt_to_equity_pct",
        "dividend_yield": "div_yield",
        "health_score_max": "health_max",
        "fcf_yield_latest_year_pct": "fcf_yield_pct",
        "profit_margins": "net_margin",
        "operating_margins": "op_margin",
        "gross_margins": "gross_margin",
        "revenue_growth": "revenue_growth",
        "earnings_growth": "earnings_growth",
    }

    out = df.reindex(columns=ordered)
    out = out.rename(columns=rename)
    return out


def main():
    print("\n" + "█" * 65)
    print("  🇮🇳  INDIAN STOCK ANALYZER — BATCH CSV EXPORT")
    print("  Paste comma-separated tickers, export metrics to CSV")
    print("█" * 65)

    # Create a new run folder each time (so we never remove/overwrite older files)
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path("batch_outputs") / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    csv_filename = out_dir / "all_tickers_comparison.csv"
    readable_csv_filename = out_dir / "all_tickers_comparison_readable.csv"
    txt_filename = out_dir / "all_tickers_comparison.txt"
    all_records = []

    while True:
        print("─" * 65)
        raw = input("  Enter tickers (comma-separated) or 'quit': ").strip()
        if raw.strip().upper() in {"QUIT", "Q", "EXIT"}:
            print("\n  👋 Exiting.\n")
            break
        if not raw.strip():
            print("  Please enter at least one ticker.")
            continue

        tickers = [t.strip().upper() for t in raw.split(",") if t.strip()]

        for t in tickers:
            if "." not in t:
                print(f"  ℹ️  No exchange specified. Trying NSE: {t}.NS")
                t = f"{t}.NS"

            print(f"\n{'█' * 65}")
            print(f"  FETCHING DATA FOR: {t}")
            print(f"{'█' * 65}")

            try:
                rec = analyze_ticker_to_record(t)
            except Exception as e:
                rec = {"ticker": t, "error": str(e)}

            all_records.append(rec)

            if rec.get("error"):
                print(f"  ❌ ERROR: {rec['error']}")
            else:
                print(f"  ✅ Data fetched: {rec.get('company_name','')}")
                print(f"  Sector: {rec.get('sector','N/A')} | Industry: {rec.get('industry','N/A')}")
                print(f"  Price: {rec.get('current_price','N/A')} | PE: {rec.get('pe_ratio_trailing','N/A')} | PB: {rec.get('pb_ratio','N/A')}")
                print(f"  Health score: {rec.get('health_score','')} / {rec.get('health_score_max','')}")

            # Full per-company report in terminal
            pretty_print_company_report(rec)

        # Write after every batch (do NOT delete/overwrite older files)
        try:
            df = pd.DataFrame(all_records)
            df.to_csv(csv_filename, index=False)
            print(f"\n  💾 CSV saved: {csv_filename} (rows: {len(all_records)})")

            # Option B readable CSV (reordered + renamed)
            readable_df = make_readable_option_b(df)
            readable_df.to_csv(readable_csv_filename, index=False)
            print(f"  💾 Readable CSV (Option B) saved: {readable_csv_filename}")

            # Comparison TXT
            _write_comparison_txt(txt_filename, all_records)
            print(f"  📝 Comparison TXT saved: {txt_filename}")
        except Exception as e:
            print(f"\n  ⚠️  Could not write CSV: {e}")

        another = input("\n  Analyze another batch? (y/n): ").strip().lower()
        if another != "y":
            print("\n  👋 Done.\n")
            break


if __name__ == "__main__":
    main()
