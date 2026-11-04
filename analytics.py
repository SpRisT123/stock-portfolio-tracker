import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests


@st.cache_data(ttl=300, show_spinner=False)
def get_asset_info(query):
    ticker = query.upper().strip()
    stock = yf.Ticker(ticker)
    hist = stock.history(period="5d")

    if hist.empty:
        results = yf.Search(query, max_results=5).quotes
        if results:
            ticker = results[0]["symbol"]
            stock = yf.Ticker(ticker)
            hist = stock.history(period="5d")

    meta = stock.history_metadata if not hist.empty else {}
    quotes = yf.Search(ticker, max_results=5).quotes
    quote = next((q for q in quotes if q["symbol"] == ticker), {})

    name = meta.get("longName") or quote.get("longname") or meta.get("shortName") or ticker
    sector = quote.get("sectorDisp") or quote.get("sector") or "ETF / Other"
    currency = meta.get("currency", "USD")
    price = float(hist["Close"].dropna().iloc[-1]) if not hist.empty else 100.0
    return ticker, name, sector, currency, price


@st.cache_data(ttl=3600, show_spinner=False)
def get_fx_rate(from_curr, to_curr):
    if from_curr == to_curr:
        return 1.0
    try:
        url = "https://api.frankfurter.app/latest"
        r = requests.get(url, params={"from": from_curr, "to": to_curr}, timeout=5)
        return float(r.json()["rates"][to_curr])
    except Exception:
        data = yf.download(f"{from_curr}{to_curr}=X", period="5d", progress=False)["Close"].squeeze()
        return float(data.dropna().iloc[-1]) if len(data) > 0 else 1.0


@st.cache_data(ttl=300)
def calculate_portfolio(positions_df, portfolio_currency="USD"):
    if positions_df.empty:
        return positions_df

    tickers = positions_df["ticker"].tolist()
    prices = yf.download(tickers, period="5d", progress=False)["Close"]
    if prices.empty:
        latest_prices = dict(zip(positions_df["ticker"], positions_df["avg_price"]))
    else:
        latest_prices = prices.ffill().iloc[-1].to_dict()

    df = positions_df.copy()
    df["current_price_raw"] = df["ticker"].map(latest_prices).fillna(df["avg_price"])

    unique_currencies = df["currency"].unique()
    fx_rates = {curr: get_fx_rate(curr, portfolio_currency) for curr in unique_currencies}
    df["fx_rate"] = df["currency"].map(fx_rates)

    df["avg_price_conv"] = df["avg_price"] * df["fx_rate"]
    df["current_price"] = df["current_price_raw"] * df["fx_rate"]
    df["cost_basis"] = df["shares"] * df["avg_price_conv"]
    df["market_value"] = df["shares"] * df["current_price"]
    df["pnl"] = df["market_value"] - df["cost_basis"]
    df["pnl_pct"] = (df["current_price"] / df["avg_price_conv"]) - 1
    df["weight"] = df["market_value"] / df["market_value"].sum()
    return df


@st.cache_data(ttl=300)
def calculate_risk_metrics(df, confidence=0.95):
    irx = yf.download("^IRX", progress=False)["Close"].squeeze()
    risk_free_rate = float(irx.iloc[-1]) / 100 if len(irx) > 0 else 0.04

    tickers = df["ticker"].tolist()
    weights = df.set_index("ticker")["weight"]

    prices = yf.download(tickers, start="2020-01-01", progress=False)["Close"]
    returns = np.log(prices / prices.shift(1)).dropna()
    if returns.empty:
        return None
    portfolio_returns = returns @ weights[returns.columns]

    hist_var = -np.percentile(portfolio_returns, (1 - confidence) * 100)
    cvar = -portfolio_returns[portfolio_returns <= -hist_var].mean()
    annual_vol = portfolio_returns.std() * np.sqrt(252)
    annual_ret = portfolio_returns.mean() * 252
    sharpe = (annual_ret - risk_free_rate) / annual_vol

    return {
        "var": hist_var,
        "cvar": cvar,
        "volatility": annual_vol,
        "sharpe": sharpe,
        "portfolio_returns": portfolio_returns
    }


@st.cache_data(ttl=300)
def calculate_markowitz(df):
    stocks = df["ticker"].tolist()
    if len(stocks) < 2:
        return None

    irx = yf.download("^IRX", progress=False)["Close"].squeeze()
    us_obligations = float(irx.iloc[-1]) / 100 if len(irx) > 0 else 0.04

    prices = yf.download(stocks, start="2020-01-01", progress=False)["Close"]
    returns = np.log(prices / prices.shift(1)).dropna()
    if returns.empty:
        return None
    mean_returns = returns.mean() * 252
    cov_matrix = returns.cov() * 252

    pr_list = []
    pvol_list = []
    sharpe_list = []
    weights_list = []

    for i in range(2000):
        weights = np.random.random(len(stocks))
        weights /= np.sum(weights)
        portfolio_return = np.sum(mean_returns * weights)
        portfolio_volatility = np.sqrt(weights @ cov_matrix @ weights)
        sharpe_ratio = (portfolio_return - us_obligations) / portfolio_volatility

        pr_list.append(portfolio_return)
        pvol_list.append(portfolio_volatility)
        sharpe_list.append(sharpe_ratio)
        weights_list.append(weights)

    argmax_sharpe = np.argmax(sharpe_list)
    max_sharpe_w = pd.Series(weights_list[argmax_sharpe], index=returns.columns)

    sim_df = pd.DataFrame({
        "Volatility": pvol_list,
        "Return": pr_list,
        "Sharpe": sharpe_list
    })
    return sim_df, max_sharpe_w


@st.cache_data(ttl=300)
def get_portfolio_history(df, period="1y"):
    tickers = df["ticker"].tolist()
    prices = yf.download(tickers, period=period, progress=False)["Close"].ffill().dropna()
    multipliers = df.set_index("ticker")["shares"] * df.set_index("ticker")["fx_rate"]
    return prices @ multipliers[prices.columns]
