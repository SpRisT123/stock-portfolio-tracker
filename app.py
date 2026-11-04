import streamlit as st
import pandas as pd
import plotly.express as px
import db
import analytics as an

st.set_page_config(page_title="Portfolio Tracker", layout="wide")
db.init_db()
color_palette = ["#660033", "#D3045D", "#E484AC", "#B3CED6", "#927B67", "#523F2B"]

st.markdown(
    """
    <style>
    header {
        display: none !important;
    }
    .st-key-positions p {
        white-space: balance !important;
        font-size: 0.95rem !important;
    }
    .block-container {
        padding-top: 1.5rem !important;
    }
    .st-key-portfolio_header button {
        border: none !important;
        background: transparent !important;
        padding: 0 !important;
    }
    .st-key-portfolio_header button p {
        font-size: 2.2rem !important;
        font-weight: 700 !important;
    }
    [data-testid="stMetricValue"] {
        font-size: 3.2rem !important;
        font-weight: 700 !important;
    }
    [data-testid="stMetricLabel"] p {
        font-size: 1.1rem !important;
    }
    .st-key-markowitz_weights [data-testid="stMetricValue"] {
        font-size: 2.2rem !important;
    }
    button[kind*="primary"] p {
        color: #000000 !important;
    }
    [role="tab"] p {
        font-size: 1rem !important;
    }
    [data-testid="InputInstructions"] {
        display: none !important;
    }   
    </style>
""",
    unsafe_allow_html=True,
)

portfolios = db.get_portfolios()

if not portfolios.empty and "portfolio_id" not in st.session_state:
    st.session_state["portfolio_id"] = int(portfolios.iloc[0]["id"])
    st.session_state["portfolio_name"] = portfolios.iloc[0]["name"]

header_label = st.session_state.get("portfolio_name", "Select Portfolio")

top_left, top_right = st.columns([5, 1])

with top_left:
    with st.container(key="portfolio_header"):
        with st.popover(header_label):
            if not portfolios.empty:
                names = list(portfolios["name"])
                current_idx = names.index(st.session_state["portfolio_name"])
                selected = st.selectbox("Switch Portfolio", names, index=current_idx)
                if selected != st.session_state["portfolio_name"]:
                    row = portfolios[portfolios["name"] == selected].iloc[0]
                    st.session_state["portfolio_id"] = int(row["id"])
                    st.session_state["portfolio_name"] = row["name"]
                    st.rerun()
                st.divider()

            new_name = st.text_input("New Portfolio Name")
            new_curr = st.selectbox("Currency", ["USD", "EUR", "PLN"])
            if (
                st.button("Create Portfolio", type="primary", width='stretch')
                and new_name
            ):
                db.add_portfolio(new_name, new_curr)
                updated = db.get_portfolios()
                new_row = updated.iloc[-1]
                st.session_state["portfolio_id"] = int(new_row["id"])
                st.session_state["portfolio_name"] = new_row["name"]
                st.rerun()

            if st.button("Reset All Data", width='stretch'):
                db.clear_db()
                st.session_state.clear()
                st.rerun()

with top_right:
    if "portfolio_id" in st.session_state:
        with st.popover("Add Transaction", width="stretch"):
            ticker = st.text_input("Ticker").upper().strip()
            default_price = 100.0
            if ticker:
                real_ticker, name, sector, asset_curr, default_price = an.get_asset_info(ticker)
                st.caption(f"{real_ticker} — {name} ({asset_curr})")
            tx_type = st.selectbox("Type", ["BUY", "SELL"])
            shares = st.number_input("Shares", min_value=0.01, value=1.0, step=1.0)
            price = st.number_input("Price", min_value=0.01, value=default_price, step=1.0)
            tx_date = st.date_input("Date")
            if st.button("Save", type="primary", width="stretch") and ticker:
                db.add_transaction(
                    st.session_state["portfolio_id"],
                    real_ticker,
                    name,
                    sector,
                    asset_curr,
                    tx_type,
                    shares,
                    price,
                    str(tx_date),
                )
                st.rerun()

if "portfolio_id" in st.session_state:
    p_row = portfolios[portfolios["id"] == st.session_state["portfolio_id"]].iloc[0]
    p_curr = p_row["currency"]

    raw_pos = db.get_positions(st.session_state["portfolio_id"])
    if not raw_pos.empty:
        df = an.calculate_portfolio(raw_pos, p_curr)
        total_val = df["market_value"].sum()
        total_cost = df["cost_basis"].sum()
        total_pnl = df["pnl"].sum()
        total_pnl_pct = (total_val / total_cost) - 1

        st.metric(
            "Total Balance",
            f"{total_val:,.2f} {p_curr}",
            f"{total_pnl:+,.2f} {p_curr} ({total_pnl_pct:+.2%})",
        )

        tab_overview, tab_risk, tab_markowitz = st.tabs(
            ["Overview", "Risk & VaR", "Markowitz"]
        )

        with tab_overview:
            with st.container(border=True, key="positions"):
                periods = {"1M": "1mo", "3M": "3mo", "6M": "6mo", "1Y": "1y", "5Y": "5y"}
                selected_p = st.segmented_control(
                "Timeframe",
                list(periods.keys()),
                default="1Y",
                label_visibility="collapsed")

                hist = an.get_portfolio_history(df, periods.get(selected_p, "1y"))
                fig_hist = px.line(
                x=hist.index,
                y=hist.values,
                labels={"x": "Date", "y": f"Value ({p_curr})"},
                color_discrete_sequence=["#5AE184"])
                fig_hist.update_traces(hovertemplate=f"%{{x}}<br><b>%{{y:,.2f}} {p_curr}</b><extra></extra>")
                st.plotly_chart(fig_hist, width='stretch')

                for i, row in df.iterrows():
                    c1, c2, c3, c4 = st.columns([2.1, 0.95, 1.25, 1.15])
                    c1.write(f"**{row['ticker']}** — {row['name']} ({row['sector']})")
                    c2.write(
                        f"Shares: **{row['shares']:.2f}** | Weight: **{row['weight']:.1%}**"
                    )
                    c3.write(
                        f"Avg: **{row['avg_price_conv']:.2f} {p_curr}** | Current: **{row['current_price']:.2f} {p_curr}**"
                    )
                    if row["pnl"] >= 0:
                        c4.write(
                            f"**{row['market_value']:.2f} {p_curr}** :green[({row['pnl']:+.2f} / {row['pnl_pct']:+.2%})]"
                        )
                    else:
                        c4.write(
                            f"**{row['market_value']:.2f} {p_curr}** :red[({row['pnl']:+.2f} / {row['pnl_pct']:+.2%})]"
                        )

            ch1, ch2 = st.columns(2)
            with ch1:
                fig1 = px.pie(
                    df,
                    values="market_value",
                    names="ticker",
                    hole=0.5,
                    title="Allocation by Asset",
                    color_discrete_sequence=color_palette,
                )
                fig1.update_traces(
                    textinfo="percent+label",
                    textposition="inside",
                    hovertemplate=f"<b>%{{label}}</b><br>%{{value:,.2f}} {p_curr} (%{{percent}})<extra></extra>",
                )
                fig1.update_layout(
                    font=dict(size=14), uniformtext_minsize=10, uniformtext_mode="hide"
                )
                st.plotly_chart(fig1, width='stretch')
            with ch2:
                fig2 = px.pie(
                    df,
                    values="market_value",
                    names="sector",
                    hole=0.5,
                    title="Allocation by Sector",
                    color_discrete_sequence=color_palette,
                )
                fig2.update_traces(
                    textinfo="percent+label",
                    textposition="inside",
                    hovertemplate=f"<b>%{{label}}</b><br>%{{value:,.2f}} {p_curr} (%{{percent}})<extra></extra>",
                )
                fig2.update_layout(uniformtext_minsize=10, uniformtext_mode="hide")
                st.plotly_chart(fig2, width='stretch')
            with st.expander("Transaction History"):
                tx_df = db.get_transactions(st.session_state["portfolio_id"])
                st.dataframe(tx_df, width='stretch', hide_index=True)

        with tab_risk:
            risk = an.calculate_risk_metrics(df)

            r1, r2, r3, r4 = st.columns(4)
            r1.metric("Daily VaR (95%)", f"{risk['var']:.2%}")
            r2.metric("Daily CVaR (95%)", f"{risk['cvar']:.2%}")
            r3.metric("Annual Volatility", f"{risk['volatility']:.2%}")
            r4.metric("Sharpe Ratio", f"{risk['sharpe']:.2f}")

            fig_var = px.histogram(
                x=risk["portfolio_returns"],
                color_discrete_sequence=["#660033"],
                nbins=100,
                labels={"x": "Daily Return"},
                title="Historical Returns & VaR (95%)",
            )
            fig_var.add_vline(
                x=-risk["var"],
                line_dash="dash",
                line_color="red",
                annotation_text="VaR 95%",
            )
            fig_var.add_vline(
                x=-risk["cvar"],
                line_dash="dot",
                line_color="orange",
                annotation_text="CVaR 95%",
            )
            fig_var.update_traces(
                hovertemplate="Return: <b>%{x:.2%}</b><br>Days: <b>%{y}</b><extra></extra>"
            )
            fig_var.update_layout(yaxis_title="Number of Days")
            st.plotly_chart(fig_var, width='stretch')

        with tab_markowitz:
            result = an.calculate_markowitz(df)
            if result is None:
                st.info(
                    "Add at least 2 different stocks to run Markowitz optimization."
                )
            else:
                sim_df, max_sharpe_w = result
                fig_m = px.scatter(
                    sim_df,
                    x="Volatility",
                    y="Return",
                    color="Sharpe",
                    title="Markowitz Efficient Frontier",
                    labels={
                        "Volatility": "Annual Volatility",
                        "Return": "Expected Annual Return",
                        "Sharpe": "Sharpe Ratio",
                    },
                    render_mode="svg",
                )
                best = sim_df.loc[sim_df["Sharpe"].idxmax()]
                fig_m.add_scatter(
                    x=[best["Volatility"]],
                    y=[best["Return"]],
                    mode="markers",
                    marker=dict(color="#f73e3e", size=16, symbol="star"),
                    name="Max Sharpe Ratio",
                    showlegend=False,
                )
                fig_m.update_traces(
                    hovertemplate="Return: <b>%{y:.2%}</b><br>Volatility: <b>%{x:.2%}</b><extra></extra>"
                )
                st.plotly_chart(fig_m, width='stretch')
                st.subheader("Optimal Weights")
                st.text(
                    "Calculated using Markowitz optimization to maximize the Sharpe ratio"
                )
                with st.container(key="markowitz_weights"):
                    cols = st.columns(10)
                    for i, (ticker_name, weight) in enumerate(max_sharpe_w.items()):
                        cols[i % 10].metric(ticker_name, f"{weight:.1%}")
    else:
        st.metric("Total Balance", f"0.00 {p_curr}")
