import sqlite3 as sql
import pandas as pd
import os

db_path = "database/portfolio.sqlite3"

def add_portfolio(name, currency="USD"):
    with sql.connect(db_path) as con:
        cursor = con.cursor()
        cursor.execute("INSERT INTO portfolios (name, currency, created_at) VALUES (?, ?, date('now'))", (name, currency))
        
def get_portfolios():
    with sql.connect(db_path) as con:
        return pd.read_sql_query("SELECT * FROM portfolios", con)

def add_transaction(portfolio_id, ticker, name, sector, currency, tx_type, shares, price, tx_date):
    with sql.connect(db_path) as con:
        cursor = con.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO assets (ticker, name, sector, currency) VALUES (?, ?, ?, ?)",
            (ticker, name, sector, currency)
        )
        cursor.execute(
            "INSERT INTO transactions (portfolio_id, ticker, tx_type, shares, price, tx_date) VALUES (?, ?, ?, ?, ?, ?)",
            (portfolio_id, ticker, tx_type, shares, price, tx_date)
        )

def get_transactions(portfolio_id):
    with sql.connect(db_path) as con:
        return pd.read_sql_query("SELECT * FROM transactions WHERE portfolio_id = ? ORDER BY tx_date DESC", con, 
                                 params=(portfolio_id,))

def get_positions(portfolio_id):
    query = """
        SELECT 
            t.ticker, a.name, a.sector, COALESCE(a.currency, 'USD') AS currency,
            SUM(CASE WHEN t.tx_type = 'BUY' THEN t.shares ELSE -t.shares END) AS shares,
            SUM(CASE WHEN t.tx_type = 'BUY' THEN t.shares * t.price ELSE 0 END) /
            SUM(CASE WHEN t.tx_type = 'BUY' THEN t.shares ELSE 0 END) AS avg_price
        FROM transactions t
        LEFT JOIN assets a ON t.ticker = a.ticker
        WHERE t.portfolio_id = ?
        GROUP BY t.ticker
        HAVING shares > 0
    """
    with sql.connect(db_path) as con:
        return pd.read_sql_query(query, con, params=(portfolio_id,))

def init_db():
    os.makedirs("database", exist_ok=True)
    with sql.connect(db_path) as con:
        cursor = con.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS portfolios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                currency TEXT NOT NULL DEFAULT 'USD',
                created_at TEXT NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS assets (
                ticker TEXT PRIMARY KEY,
                name TEXT,
                sector TEXT,
                currency TEXT DEFAULT 'USD'
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                portfolio_id INTEGER NOT NULL,
                ticker TEXT NOT NULL,
                tx_type TEXT NOT NULL,
                shares REAL NOT NULL,
                price REAL NOT NULL,
                tx_date TEXT NOT NULL,
                FOREIGN KEY (portfolio_id) REFERENCES portfolios(id),
                FOREIGN KEY (ticker) REFERENCES assets(ticker)
            )
        """)

def clear_db():
    with sql.connect(db_path) as con:
        cursor = con.cursor()
        cursor.execute("DELETE FROM transactions")
        cursor.execute("DELETE FROM portfolios")
        cursor.execute("DELETE FROM assets")
        cursor.execute("DELETE FROM sqlite_sequence")
    
