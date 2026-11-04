# Portfolio Tracker

Multi-currency portfolio tracker in Python (`Streamlit`, `SQLite`, `Plotly`, `yfinance`) with VaR/CVaR risk analytics and Markowitz portfolio optimization.

## Features
- Local SQLite database (`db.py`) for storing multiple portfolios, assets, and BUY/SELL transactions
- Automatic ticker lookup for US & European stocks (e.g. GPW `.WA`, Xetra `.DE`) and live FX conversion (`USD`, `EUR`, `PLN`)
- Portfolio valuation chart (`1M`, `3M`, `6M`, `1Y`, `5Y`), P&L breakdown, and asset/sector allocation charts
- Historical Value at Risk ($\text{VaR}_{95\%}$), Expected Shortfall ($\text{CVaR}_{95\%}$), annualized volatility, and Sharpe Ratio
- Monte Carlo Markowitz Efficient Frontier simulation for optimal portfolio weights

## Screenshots

![Portfolio Value](images/overview1.png)

![Holdings & Allocation](images/overview2.png)

![Risk & VaR](images/risk%20%26%20var.png)

![Markowitz Frontier](images/markowitz.png)

## Run
```bash
streamlit run app.py
```
