"""
============================================================
  INDIAN STOCK ANALYZER — Income Statement + Ratios + Cash Flow
  Data Source : Yahoo Finance (Free, No API Key needed)
============================================================

SETUP — Run this ONE TIME in your terminal:
    pip install yfinance pandas tabulate openpyxl

HOW TO RUN:
    python stock_analyzer.py

TICKER SYMBOL FORMAT:
    NSE stocks → Add .NS   e.g. HINDUNILVR.NS
    BSE stocks → Add .BO   e.g. HINDUNILVR.BO

COMMON TICKERS:
    HUL          → HINDUNILVR.NS
    TCS          → TCS.NS
    Sun Pharma   → SUNPHARMA.NS
    Infosys      → INFY.NS
    HDFC Bank    → HDFCBANK.NS
    Reliance     → RELIANCE.NS
    Asian Paints → ASIANPAINT.NS
    Maruti       → MARUTI.NS
    Wipro        → WIPRO.NS
    Bajaj Finance→ BAJFINANCE.NS
"""

import yfinance as yf
import pandas as pd
from tabulate import tabulate
import os
from datetime import datetime
from pathlib import Path
import warnings
warnings.filterwarnings("ignore")


# ─────────────────────────────────────────────
#  CONFIGURATION — Change colors/settings here
# ─────────────────────────────────────────────

SAVE_TO_CSV = False            # Set False if you don't want CSV file
SHOW_IN_CRORES = True         # True = show in ₹ Crores | False = raw numbers
YEARS_TO_SHOW = 5             # How many years of historical data

# Dividend/"interest" estimate: use a fixed notional investment amount
# (user requested: don't ask for user inputs)
DEFAULT_INVESTMENT_INR = 100_000


# ─────────────────────────────────────────────
#  HELPER FUNCTIONS
# ─────────────────────────────────────────────

def convert_to_crores(value):
    """Convert raw number to Indian Crores"""
    if pd.isna(value) or value is None:
        return "N/A"
    return round(value / 1e7, 2)  # 1 Crore = 10 Million = 10,000,000


def format_value(value, is_ratio=False, is_percent=False):
    """Format value for display"""
    # Normalize common "missing" representations coming from yfinance or our helpers
    if value is None:
        return "N/A"
    if isinstance(value, str):
        if value.strip().upper() in {"N/A", "NA", "NONE", "NULL", ""}:
            return "N/A"
    else:
        # For numpy/pandas NaN
        try:
            if pd.isna(value):
                return "N/A"
        except Exception:
            pass

    if is_ratio or is_percent:
        try:
            num = float(value)
        except Exception:
            return "N/A"
        suffix = "x" if is_ratio else "%"
        return f"{round(num, 2)}{suffix}"

    if SHOW_IN_CRORES and not is_ratio and not is_percent:
        return f"₹{value} Cr"
    return str(value)


def get_safe(data, key, default=None):
    """Safely get value from dict"""
    try:
        val = data.get(key, default)
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return "N/A"
        return val
    except:
        return "N/A"


def print_header(title):
    """Print a formatted section header"""
    print("\n" + "═" * 65)
    print(f"  {title}")
    print("═" * 65)


def print_divider():
    print("─" * 65)


# ─────────────────────────────────────────────
#  CORE ANALYSIS FUNCTION
# ─────────────────────────────────────────────

def analyze_stock(ticker_symbol):
    """
    Main function — fetches and displays all financial data
    for a given stock ticker.
    """

    print(f"\n{'█' * 65}")
    print(f"  FETCHING DATA FOR: {ticker_symbol.upper()}")
    print(f"{'█' * 65}")
    print("  Please wait...")

    # ── Fetch Data ──
    try:
        stock = yf.Ticker(ticker_symbol)
        info = stock.info
        # print(f" stock info - {info}")
        # Check if ticker is valid
        if not info or info.get("regularMarketPrice") is None and info.get("currentPrice") is None:
            print(f"\n  ❌ ERROR: Could not find data for '{ticker_symbol}'")
            print(f"  Make sure ticker is correct. Example: HINDUNILVR.NS for HUL on NSE")
            return

        company_name = get_safe(info, "longName", ticker_symbol)
        sector = get_safe(info, "sector", "N/A")
        industry = get_safe(info, "industry", "N/A")
        exchange = get_safe(info, "exchange", "N/A")

        print(f"\n  ✅ Data fetched successfully!")
        print(f"  Company  : {company_name}")
        print(f"  Sector   : {sector}")
        print(f"  Industry : {industry}")
        print(f"  Exchange : {exchange}")

    except Exception as e:
        print(f"\n  ❌ ERROR fetching data: {e}")
        print("  Check your internet connection and ticker symbol.")
        return


    # ════════════════════════════════════════
    #  SECTION 1 — CURRENT MARKET SNAPSHOT
    # ════════════════════════════════════════

    print_header("📊 CURRENT MARKET SNAPSHOT")

    current_price = get_safe(info, "currentPrice") or get_safe(info, "regularMarketPrice")
    prev_close    = get_safe(info, "previousClose")
    week52_high   = get_safe(info, "fiftyTwoWeekHigh")
    week52_low    = get_safe(info, "fiftyTwoWeekLow")
    market_cap    = get_safe(info, "marketCap")
    currency      = get_safe(info, "currency", "INR")

    # Calculate % from 52W high and low
    try:
        pct_from_high = round(((float(current_price) - float(week52_high)) / float(week52_high)) * 100, 2)
        pct_from_low  = round(((float(current_price) - float(week52_low))  / float(week52_low))  * 100, 2)
        from_high_str = f"{pct_from_high}% from High"
        from_low_str  = f"+{pct_from_low}% from Low"
    except:
        from_high_str = "N/A"
        from_low_str  = "N/A"

    snapshot_data = [
        ["Current Price",    f"₹{current_price}"],
        ["Previous Close",   f"₹{prev_close}"],
        ["52 Week High",     f"₹{week52_high}  ({from_high_str})"],
        ["52 Week Low",      f"₹{week52_low}  ({from_low_str})"],
        ["Market Cap",       f"₹{convert_to_crores(market_cap)} Cr" if market_cap != "N/A" else "N/A"],
        ["Currency",         currency],
    ]
    print(tabulate(snapshot_data, tablefmt="simple", colalign=("left", "right")))


    # ════════════════════════════════════════
    #  QUICK LINKS — External context
    # ════════════════════════════════════════

    print_header("🔗 USEFUL LINKS")

    # Create links for quick context (works best for NSE/BSE tickers)
    try:
        base_symbol = ticker_symbol.upper().split(".")[0]
    except Exception:
        base_symbol = ticker_symbol.upper()

    # These are plain links (copy/paste). Some sites may rate-limit or require manual search.
    links_data = [
        ["Yahoo Finance",  f"https://finance.yahoo.com/quote/{ticker_symbol.upper()}"] ,
        ["Screener.in",    f"https://www.screener.in/company/{base_symbol}/"],
        ["Moneycontrol",  f"https://www.moneycontrol.com/india/stockpricequote/search?search_str={base_symbol}"],
        ["NSE (search)",  f"https://www.nseindia.com/search?q={base_symbol}"],
    ]
    print(tabulate(links_data, tablefmt="simple", colalign=("left", "left")))


    # ════════════════════════════════════════
    #  SECTION 2 — KEY RATIOS
    # ════════════════════════════════════════

    print_header("📐 KEY RATIOS")

    pe_ratio      = get_safe(info, "trailingPE")
    forward_pe    = get_safe(info, "forwardPE")
    pb_ratio      = get_safe(info, "priceToBook")
    ps_ratio      = get_safe(info, "priceToSalesTrailing12Months")
    roe           = get_safe(info, "returnOnEquity")
    roa           = get_safe(info, "returnOnAssets")
    debt_equity   = get_safe(info, "debtToEquity")
    current_ratio = get_safe(info, "currentRatio")
    quick_ratio   = get_safe(info, "quickRatio")
    div_yield     = get_safe(info, "dividendYield")
    beta          = get_safe(info, "beta")
    eps           = get_safe(info, "trailingEps")
    forward_eps   = get_safe(info, "forwardEps")
    peg_ratio     = get_safe(info, "pegRatio")

    # Basic shares + Basic EPS (some platforms/yfinance differ from trailingEps)
    # NOTE: sharesOutstanding is typically basic shares count.
    shares_basic = get_safe(info, "sharesOutstanding")  # Basic shares

    # Compute Basic EPS
    try:
        net_income_val = stock.financials.loc["Net Income", stock.financials.columns[0]]
        basic_eps = round(net_income_val / float(shares_basic), 2) if shares_basic != "N/A" else "N/A"
    except:
        basic_eps = "N/A"

    # Compute Basic P/E using our computed Basic EPS
    try:
        _cp = float(current_price)
        _be = float(basic_eps)
        basic_pe = round(_cp / _be, 2) if _be != 0 else "N/A"
    except:
        basic_pe = "N/A"

    # Convert decimal fraction -> percent (e.g. 0.0184 -> 1.84)
    # If the value already looks like a percent (>1), keep as-is.
    def to_pct(val):
        try:
            f = float(val)
            return round(f * 100, 2) if f <= 1 else round(f, 2)
        except:
            return "N/A"

    ratios_data = [
        ["─── VALUATION ───",         ""],
        ["P/E Ratio (Trailing)",       format_value(pe_ratio, is_ratio=True)],
        ["P/E Ratio (Forward)",        format_value(forward_pe, is_ratio=True)],
        ["P/E Ratio (Basic)",          format_value(basic_pe, is_ratio=True)],
        ["P/B Ratio",                  format_value(pb_ratio, is_ratio=True)],
        ["P/S Ratio",                  format_value(ps_ratio, is_ratio=True)],
        ["PEG Ratio",                  format_value(peg_ratio, is_ratio=True)],
        ["EPS (Trailing)",             f"₹{round(float(eps),2)}" if eps != "N/A" else "N/A"],
        ["EPS (Forward)",              f"₹{round(float(forward_eps),2)}" if forward_eps != "N/A" else "N/A"],
        ["EPS (Basic)",                f"₹{basic_eps}" if basic_eps != "N/A" else "N/A"],
        ["─── PROFITABILITY ───",      ""],
        ["ROE (Return on Equity)",     format_value(to_pct(roe), is_percent=True)],
        ["ROA (Return on Assets)",     format_value(to_pct(roa), is_percent=True)],
        ["─── DEBT & LIQUIDITY ───",   ""],
        ["Debt/Equity Ratio",          format_value(debt_equity / 100 if debt_equity != "N/A" else "N/A", is_ratio=True)],
        ["Current Ratio",              format_value(current_ratio, is_ratio=True)],
        ["Quick Ratio",                format_value(quick_ratio, is_ratio=True)],
        ["─── DIVIDEND & RISK ───",    ""],
        ["Dividend Yield",             format_value(to_pct(div_yield), is_percent=True)],
        ["Beta",                       format_value(beta)],
    ]
    print(tabulate(ratios_data, tablefmt="simple", colalign=("left", "right")))


    # ════════════════════════════════════════
    #  SECTION 2B — VALUATION & EPS HISTORY (5Y yearly + quarterly)
    # ════════════════════════════════════════

    print_header("📆 VALUATION & EPS HISTORY — 5Y (Yearly) + Recent Quarters")

    def _safe_float(v):
        try:
            if v is None or v == "N/A" or (isinstance(v, float) and pd.isna(v)):
                return None
            return float(v)
        except Exception:
            return None

    def _fmt_ratio(v):
        return "N/A" if v is None else f"{v:.2f}x"

    def _fmt_eps(v):
        return "N/A" if v is None else f"₹{v:.2f}"

    def _fmt_pct(v):
        return "N/A" if v is None else f"{v:.2f}%"

    # --- Yearly (use last 5 fiscal years from annual financials) ---
    try:
        inc = stock.financials
        years_table = []
        if inc is not None and not inc.empty:
            inc = inc.iloc[:, :YEARS_TO_SHOW]
            years = [str(c.year) for c in inc.columns]

            for col, year in zip(inc.columns, years):
                # yfinance annual columns are newest->older
                try:
                    net_income_y = inc.loc["Net Income", col]
                except Exception:
                    net_income_y = None

                eps_y = None
                pe_y = None
                pb_y = None

                try:
                    if shares_basic not in ("N/A", None) and net_income_y is not None and not pd.isna(net_income_y):
                        eps_y = float(net_income_y) / float(shares_basic)
                except Exception:
                    eps_y = None

                # We don't have historical prices per fiscal year in fundamentals,
                # so we compute *implied* historical P/E and P/B using CURRENT price.
                # This still helps compare earnings/book trend impact.
                try:
                    cp = _safe_float(current_price)
                    if cp is not None and eps_y not in (None, 0):
                        pe_y = cp / float(eps_y)
                except Exception:
                    pe_y = None

                try:
                    # priceToBook is current; implied book value per share ≈ current_price / current_pb
                    cp = _safe_float(current_price)
                    cur_pb = _safe_float(pb_ratio)
                    if cp is not None and cur_pb not in (None, 0):
                        bvps_est = cp / cur_pb
                        if bvps_est not in (None, 0):
                            pb_y = cp / bvps_est  # will equal cur_pb, but kept for table symmetry
                except Exception:
                    pb_y = None

                years_table.append([year, _fmt_ratio(pe_y), _fmt_ratio(pb_y if pb_y is not None else _safe_float(pb_ratio)), _fmt_eps(eps_y)])

            print("\n  YEARLY (last 5 fiscal years) — (P/E & P/B are implied using current price)")
            print(tabulate(years_table, headers=["Year", "P/E", "P/B", "EPS"], tablefmt="simple"))
        else:
            print("  ⚠️  Annual financials not available to compute yearly EPS history.")
    except Exception as e:
        print(f"  ⚠️  Could not compute yearly history: {e}")

    # --- Quarterly (use last N quarters from quarterly_financials) ---
    try:
        qinc = stock.quarterly_financials
        q_table = []
        if qinc is not None and not qinc.empty:
            # show up to last 8 quarters (newest->older)
            qinc = qinc.iloc[:, :8]
            quarters = [c.strftime("%Y-Q%q") if hasattr(c, "quarter") else str(c) for c in qinc.columns]
            # pandas Timestamp has .quarter, but strftime %q isn't standard; build manually.
            quarters = []
            for c in qinc.columns:
                try:
                    quarters.append(f"{c.year}-Q{c.quarter}")
                except Exception:
                    quarters.append(str(c))

            for col, q in zip(qinc.columns, quarters):
                try:
                    net_income_q = qinc.loc["Net Income", col]
                except Exception:
                    net_income_q = None

                eps_q = None
                pe_q = None
                pb_q = None

                try:
                    if shares_basic not in ("N/A", None) and net_income_q is not None and not pd.isna(net_income_q):
                        eps_q = float(net_income_q) / float(shares_basic)
                except Exception:
                    eps_q = None

                try:
                    cp = _safe_float(current_price)
                    if cp is not None and eps_q not in (None, 0):
                        pe_q = cp / float(eps_q)
                except Exception:
                    pe_q = None

                # P/B quarterly isn't meaningful without quarterly equity; we show current P/B
                pb_q = _safe_float(pb_ratio)

                q_table.append([q, _fmt_ratio(pe_q), _fmt_ratio(pb_q), _fmt_eps(eps_q)])

            print("\n  QUARTERLY (last 8 quarters) — (P/E is implied using current price)")
            print(tabulate(q_table, headers=["Quarter", "P/E", "P/B", "EPS"], tablefmt="simple"))
        else:
            print("  ⚠️  Quarterly financials not available to compute quarterly EPS history.")
    except Exception as e:
        print(f"  ⚠️  Could not compute quarterly history: {e}")


    # ════════════════════════════════════════
    #  SECTION 2C — DIVIDEND / "INTEREST" ESTIMATE (fixed investment)
    # ════════════════════════════════════════

    print_header("💵 DIVIDEND (\"INTEREST\") ESTIMATE — Based on Fixed Investment")

    try:
        cp = _safe_float(current_price)
        dy = _safe_float(div_yield)

        # dividendYield from yfinance is usually a fraction (0.01 = 1%)
        if dy is not None and dy > 1:
            # looks like already % (bad data) => convert to fraction-ish
            dy_frac = dy / 100
        else:
            dy_frac = dy

        if cp is None or dy_frac is None:
            print("  ⚠️  Dividend yield/current price not available to estimate dividend income.")
        else:
            shares_est = DEFAULT_INVESTMENT_INR / cp if cp > 0 else 0
            annual_div_income = DEFAULT_INVESTMENT_INR * dy_frac

            div_table = [
                ["Assumed Investment", f"₹{DEFAULT_INVESTMENT_INR:,.0f}"],
                ["Estimated Shares", f"{shares_est:,.2f}"],
                ["Dividend Yield", _fmt_pct(dy_frac * 100)],
                ["Est. Annual Dividend Income", f"₹{annual_div_income:,.0f} / year"],
            ]
            print(tabulate(div_table, tablefmt="simple", colalign=("left", "right")))
    except Exception as e:
        print(f"  ⚠️  Could not compute dividend estimate: {e}")

    # Ratio Interpretation
    print("\n  💡 QUICK INTERPRETATION:")
    try:
        pe = float(pe_ratio)
        if pe < 15:     print(f"  P/E {pe}x → Potentially undervalued (low expectations)")
        elif pe < 30:   print(f"  P/E {pe}x → Fair valuation range")
        elif pe < 50:   print(f"  P/E {pe}x → Premium valuation (high growth expected)")
        else:           print(f"  P/E {pe}x → Very expensive, growth must justify this")
    except: pass

    try:
        roe_pct = to_pct(roe)
        if roe_pct != "N/A":
            if float(roe_pct) >= 20:   print(f"  ROE {roe_pct}% → Excellent capital efficiency ✅")
            elif float(roe_pct) >= 15: print(f"  ROE {roe_pct}% → Good capital efficiency ✅")
            else:                      print(f"  ROE {roe_pct}% → Below average, check why ⚠️")
    except: pass

    try:
        de = debt_equity / 100 if debt_equity != "N/A" else "N/A"
        if de != "N/A":
            if float(de) < 0.5:   print(f"  D/E {round(float(de),2)}x → Very low debt, financially safe ✅")
            elif float(de) < 1.5: print(f"  D/E {round(float(de),2)}x → Moderate debt, acceptable ✅")
            elif float(de) < 2.5: print(f"  D/E {round(float(de),2)}x → High debt, monitor closely ⚠️")
            else:                  print(f"  D/E {round(float(de),2)}x → Very high debt, risky ❌")
    except: pass


    # ════════════════════════════════════════
    #  SECTION 3 — INCOME STATEMENT (5 Years)
    # ════════════════════════════════════════

    print_header("📈 INCOME STATEMENT — Last 5 Years (₹ Crores)")

    try:
        income_stmt = stock.financials  # Annual financials
        if income_stmt is not None and not income_stmt.empty:

            # Select last N years
            income_stmt = income_stmt.iloc[:, :YEARS_TO_SHOW]
            years = [str(col.year) for col in income_stmt.columns]

            # Rows we want to display
            income_rows = {
                "Total Revenue":        "Total Revenue",
                "Cost Of Revenue":      "Cost Of Revenue",
                "Gross Profit":         "Gross Profit",
                "Operating Income":     "Operating Income",
                "EBITDA":               "EBITDA",
                "Pretax Income":        "Pretax Income",
                "Tax Provision":        "Tax Provision",
                "Net Income":           "Net Income",
            }

            table_data = [["Metric"] + years]
            for display_name, yf_key in income_rows.items():
                row = [display_name]
                for col in income_stmt.columns:
                    try:
                        val = income_stmt.loc[yf_key, col]
                        row.append(f"₹{convert_to_crores(val):,.0f}" if val != "N/A" else "N/A")
                    except:
                        row.append("N/A")
                table_data.append(row)

            # Calculate and add margins
            print(tabulate(table_data[1:], headers=table_data[0], tablefmt="simple"))

            # Margin calculations
            print("\n  📊 MARGIN ANALYSIS:")
            margin_rows = []
            for margin_name, numerator_key, denominator_key in [
                ("Gross Margin %",     "Gross Profit",     "Total Revenue"),
                ("Operating Margin %", "Operating Income", "Total Revenue"),
                ("Net Margin %",       "Net Income",       "Total Revenue"),
            ]:
                row = [margin_name]
                for col in income_stmt.columns:
                    try:
                        num = income_stmt.loc[numerator_key, col]
                        den = income_stmt.loc[denominator_key, col]
                        margin = round((num / den) * 100, 2)
                        row.append(f"{margin}%")
                    except:
                        row.append("N/A")
                margin_rows.append(row)
            print(tabulate(margin_rows, headers=["Metric"] + years, tablefmt="simple"))

        else:
            print("  ⚠️  Income statement data not available for this ticker.")

    except Exception as e:
        print(f"  ⚠️  Could not fetch income statement: {e}")


    # ════════════════════════════════════════
    #  SECTION 4 — CASH FLOW STATEMENT
    # ════════════════════════════════════════

    print_header("💰 CASH FLOW STATEMENT — Last 5 Years (₹ Crores)")

    try:
        cashflow = stock.cashflow
        if cashflow is not None and not cashflow.empty:

            cashflow = cashflow.iloc[:, :YEARS_TO_SHOW]
            years = [str(col.year) for col in cashflow.columns]

            cashflow_rows = {
                "Operating Cash Flow":   "Operating Cash Flow",
                "Capital Expenditure":   "Capital Expenditure",
                "Investing Cash Flow":   "Investing Cash Flow",
                "Financing Cash Flow":   "Financing Cash Flow",
                "Free Cash Flow":        "Free Cash Flow",
            }

            table_data = []
            for display_name, yf_key in cashflow_rows.items():
                row = [display_name]
                for col in cashflow.columns:
                    try:
                        val = cashflow.loc[yf_key, col]
                        converted = convert_to_crores(val)
                        # Add negative indicator for outflows
                        prefix = "₹" if float(converted) >= 0 else "₹"
                        row.append(f"{prefix}{converted:,.0f}")
                    except:
                        row.append("N/A")
                table_data.append(row)

            print(tabulate(table_data, headers=["Metric"] + years, tablefmt="simple"))

            # FCF Yield calculation
            try:
                latest_fcf = cashflow.loc["Free Cash Flow", cashflow.columns[0]]
                mcap = info.get("marketCap")
                if latest_fcf and mcap:
                    fcf_yield = round((latest_fcf / mcap) * 100, 2)
                    print(f"\n  💡 FCF Yield (Latest Year) = {fcf_yield}%")
                    if fcf_yield > 5:
                        print(f"  Strong FCF yield — company generating good real cash ✅")
                    elif fcf_yield > 2:
                        print(f"  Moderate FCF yield — acceptable ✅")
                    else:
                        print(f"  Low FCF yield — check if capex heavy phase or weak business ⚠️")
            except: pass

        else:
            print("  ⚠️  Cash flow data not available for this ticker.")

    except Exception as e:
        print(f"  ⚠️  Could not fetch cash flow: {e}")


    # ════════════════════════════════════════
    #  SECTION 5 — BALANCE SHEET SNAPSHOT
    # ════════════════════════════════════════

    print_header("🏦 BALANCE SHEET SNAPSHOT (₹ Crores)")

    try:
        balance_sheet = stock.balance_sheet
        if balance_sheet is not None and not balance_sheet.empty:

            balance_sheet = balance_sheet.iloc[:, :YEARS_TO_SHOW]
            years = [str(col.year) for col in balance_sheet.columns]

            bs_rows = {
                "Total Assets":              "Total Assets",
                "Total Liabilities Net Minority Interest": "Total Liabilities",
                "Stockholders Equity":       "Stockholders Equity",
                "Total Debt":                "Total Debt",
                "Cash And Cash Equivalents": "Cash & Equivalents",
            }

            table_data = []
            for display_name, yf_key in bs_rows.items():
                row = [display_name]
                for col in balance_sheet.columns:
                    try:
                        val = balance_sheet.loc[yf_key, col]
                        row.append(f"₹{convert_to_crores(val):,.0f}")
                    except:
                        row.append("N/A")
                table_data.append(row)

            print(tabulate(table_data, headers=["Metric"] + years, tablefmt="simple"))

        else:
            print("  ⚠️  Balance sheet data not available.")

    except Exception as e:
        print(f"  ⚠️  Could not fetch balance sheet: {e}")


    # ════════════════════════════════════════
    #  SECTION 6 — OVERALL HEALTH SCORECARD
    # ════════════════════════════════════════

    print_header("🎯 OVERALL HEALTH SCORECARD")

    score = 0
    max_score = 0
    scorecard = []

    def check(condition, label, good_msg, bad_msg):
        nonlocal score, max_score
        max_score += 1
        if condition:
            score += 1
            scorecard.append([f"✅ {label}", good_msg])
        else:
            scorecard.append([f"❌ {label}", bad_msg])

    try:
        roe_val = to_pct(roe)
        check(roe_val != "N/A" and float(roe_val) >= 15,
              "ROE", f"{roe_val}% — Good efficiency", f"{roe_val}% — Below 15% threshold")
    except: pass

    try:
        de_val = debt_equity / 100 if debt_equity != "N/A" else "N/A"
        check(de_val != "N/A" and float(de_val) < 1.0,
              "D/E Ratio", f"{round(float(de_val),2)}x — Safe debt level", f"{round(float(de_val),2)}x — High debt")
    except: pass

    try:
        check(pe_ratio != "N/A" and float(pe_ratio) > 0,
              "P/E Ratio", f"{round(float(pe_ratio),1)}x — Positive earnings", "Negative/No earnings")
    except: pass

    try:
        check(pb_ratio != "N/A" and float(pb_ratio) > 0,
              "P/B Ratio", f"{round(float(pb_ratio),2)}x — Trading above book value", "Below book value")
    except: pass

    try:
        check(current_ratio != "N/A" and float(current_ratio) >= 1.5,
              "Current Ratio", f"{round(float(current_ratio),2)}x — Good liquidity", f"Low liquidity, may struggle with short term debt")
    except: pass

    print(tabulate(scorecard, tablefmt="simple", colalign=("left", "left")))
    print(f"\n  SCORE: {score}/{max_score} parameters healthy")

    if score == max_score:
        print("  🏆 Excellent — Strong across all checked parameters!")
    elif score >= max_score * 0.7:
        print("  👍 Good — Most parameters healthy, minor concerns")
    elif score >= max_score * 0.5:
        print("  ⚠️  Average — Several parameters need attention")
    else:
        print("  ❌ Weak — Fundamental concerns, research carefully before investing")


    # ════════════════════════════════════════
    #  SECTION 7 — LATEST NEWS
    # ════════════════════════════════════════

    print_header("📰 LATEST NEWS")

    try:
        news = stock.news  # yfinance built-in news fetch
        def _has_useful_news_item(a: dict) -> bool:
            try:
                t = (a.get("title") or "").strip()
                l = (a.get("link") or "").strip()
                p = (a.get("publisher") or "").strip()
                return bool(t or l or p)
            except Exception:
                return False

        useful_news = [a for a in (news or []) if _has_useful_news_item(a)]

        if useful_news:
            for i, article in enumerate(useful_news[:5], 1):  # Show top 5 news
                title = article.get("title") or "(No title provided)"
                publisher = article.get("publisher") or "Unknown"
                link = article.get("link") or "(No link)"

                # Convert Unix timestamp to readable date
                pub_time = article.get("providerPublishTime", None)
                if pub_time:
                    date_str = datetime.fromtimestamp(pub_time).strftime("%d %b %Y, %I:%M %p")
                else:
                    date_str = "N/A"

                print(f"\n  [{i}] {title}")
                print(f"      Publisher: {publisher}  |  Time: {date_str}")
                print(f"      Link     : {link}")
                print("  " + "─" * 60)
        else:
            # yfinance sometimes returns empty placeholders. Avoid printing 5 useless rows.
            print("  ⚠️  No usable news available from Yahoo for this ticker.")
            print("  ℹ️  Tip: use the links above (Screener/Moneycontrol/NSE) for latest updates.")

    except Exception as e:
        print(f"  ⚠️  Could not fetch news: {e}")


    # ════════════════════════════════════════
    #  SAVE TO CSV
    # ════════════════════════════════════════

    if SAVE_TO_CSV:
        try:
            base = ticker_symbol.replace('.', '_')
            ratios_filename = f"{base}_key_ratios.csv"
            income_filename = f"{base}_income_statement.csv"
            cashflow_filename = f"{base}_cash_flow.csv"
            balancesheet_filename = f"{base}_balance_sheet.csv"

            # Key ratios (single table)
            ratios_df = pd.DataFrame([
                {"Metric": "P/E Ratio (Trailing)", "Value": pe_ratio},
                {"Metric": "P/E Ratio (Forward)",  "Value": forward_pe},
                {"Metric": "P/E Ratio (Basic)",    "Value": basic_pe},
                {"Metric": "P/B Ratio",             "Value": pb_ratio},
                {"Metric": "P/S Ratio",             "Value": ps_ratio},
                {"Metric": "PEG Ratio",             "Value": peg_ratio},
                {"Metric": "ROE (%)",               "Value": to_pct(roe)},
                {"Metric": "ROA (%)",               "Value": to_pct(roa)},
                {"Metric": "D/E Ratio",             "Value": round(debt_equity/100, 2) if debt_equity != "N/A" else "N/A"},
                {"Metric": "EPS (Trailing)",        "Value": eps},
                {"Metric": "EPS (Forward)",         "Value": forward_eps},
                {"Metric": "EPS (Basic)",           "Value": basic_eps},
                {"Metric": "Beta",                  "Value": beta},
                {"Metric": "Dividend Yield (%)",    "Value": to_pct(div_yield)},
                {"Metric": "Current Ratio",         "Value": current_ratio},
                {"Metric": "Quick Ratio",           "Value": quick_ratio},
            ])
            ratios_df.to_csv(ratios_filename, index=False)

            # Financial statements (each as its own CSV)
            if stock.financials is not None and not stock.financials.empty:
                inc = stock.financials.iloc[:, :YEARS_TO_SHOW].copy()
                inc = inc.applymap(lambda x: convert_to_crores(x) if pd.notna(x) else "N/A")
                inc.to_csv(income_filename)

            if stock.cashflow is not None and not stock.cashflow.empty:
                cf = stock.cashflow.iloc[:, :YEARS_TO_SHOW].copy()
                cf = cf.applymap(lambda x: convert_to_crores(x) if pd.notna(x) else "N/A")
                cf.to_csv(cashflow_filename)

            if stock.balance_sheet is not None and not stock.balance_sheet.empty:
                bs = stock.balance_sheet.iloc[:, :YEARS_TO_SHOW].copy()
                bs = bs.applymap(lambda x: convert_to_crores(x) if pd.notna(x) else "N/A")
                bs.to_csv(balancesheet_filename)

            print(f"\n  💾 CSV files saved:")
            print(f"     - {ratios_filename}")
            if os.path.exists(income_filename):
                print(f"     - {income_filename}")
            if os.path.exists(cashflow_filename):
                print(f"     - {cashflow_filename}")
            if os.path.exists(balancesheet_filename):
                print(f"     - {balancesheet_filename}")

        except Exception as e:
            print(f"\n  ⚠️  Could not save CSV: {e}")

    print(f"\n{'█' * 65}")
    print(f"  ANALYSIS COMPLETE — {company_name}")
    print(f"{'█' * 65}\n")


# ─────────────────────────────────────────────
#  MAIN — Entry Point
# ─────────────────────────────────────────────

def main():
    # Store logs in a single folder, but use a human-readable timestamped filename
    out_dir = Path("runs")
    out_dir.mkdir(parents=True, exist_ok=True)

    # Example filename: 26feb_06-34PM.txt (avoid ':' for filesystem compatibility)
    log_filename = datetime.now().strftime("%d%b_%I-%M%p").lower() + ".txt"
    log_path = out_dir / log_filename
    try:
        import sys
        original_stdout = sys.stdout
        log_fh = open(log_path, "w", encoding="utf-8")

        class _Tee:
            def __init__(self, *streams):
                self.streams = streams

            def write(self, data):
                for s in self.streams:
                    s.write(data)

            def flush(self):
                for s in self.streams:
                    s.flush()

        sys.stdout = _Tee(original_stdout, log_fh)
    except Exception:
        log_fh = None

    print("\n" + "█" * 65)
    print("  🇮🇳  INDIAN STOCK ANALYZER")
    print("  Income Statement | Key Ratios | Cash Flow | Balance Sheet")
    print("█" * 65)

    print(f"\n  📁 Log folder : {out_dir}")
    print(f"  📝 Output log : {log_path.name}")

    print("""
  TICKER FORMAT:
  ┌─────────────────┬─────────────────────┐
  │ Company         │ Ticker Symbol       │
  ├─────────────────┼─────────────────────┤
  │ HUL             │ HINDUNILVR.NS       │
  │ TCS             │ TCS.NS              │
  │ Sun Pharma      │ SUNPHARMA.NS        │
  │ Infosys         │ INFY.NS             │
  │ HDFC Bank       │ HDFCBANK.NS         │
  │ Reliance        │ RELIANCE.NS         │
  │ Asian Paints    │ ASIANPAINT.NS       │
  │ Maruti Suzuki   │ MARUTI.NS           │
  │ Bajaj Finance   │ BAJFINANCE.NS       │
  │ Wipro           │ WIPRO.NS            │
  └─────────────────┴─────────────────────┘
    """)

    while True:
        print("─" * 65)
        raw = input("  Enter ticker symbol(s) (comma-separated) or 'quit' to exit: ").strip().upper()

        if raw in ["QUIT", "Q", "EXIT"]:
            print("\n  👋 Exiting. Happy investing!\n")
            break

        if not raw:
            print("  Please enter at least one valid ticker symbol.")
            continue

        tickers = [t.strip() for t in raw.split(",") if t.strip()]

        for ticker in tickers:
            # Auto-add .NS if user forgets
            if "." not in ticker:
                auto_ticker = ticker + ".NS"
                print(f"  ℹ️  No exchange specified. Trying NSE: {auto_ticker}")
                ticker = auto_ticker

            analyze_stock(ticker)

        another = input("\n  Analyze another stock? (y/n): ").strip().lower()
        if another != "y":
            print("\n  👋 Happy investing!\n")
            break

    # restore stdout + close log
    try:
        import sys
        if 'original_stdout' in locals():
            sys.stdout = original_stdout
        if log_fh:
            log_fh.close()
    except Exception:
        pass


if __name__ == "__main__":
    main()