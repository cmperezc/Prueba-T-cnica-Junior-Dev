import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB = ROOT / "data" / "orders.sqlite3"

def read_orders():
    return json.loads((ROOT / "data" / "orders.json").read_text(encoding="utf-8"))

def main():
    DB.parent.mkdir(exist_ok=True)
    orders = read_orders()
    with sqlite3.connect(DB) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY,
                customer TEXT NOT NULL,
                total REAL NOT NULL CHECK(total >= 0),
                status TEXT NOT NULL CHECK(status IN ('pendiente','enviado','cancelado'))
            )
        """)
        con.executemany("INSERT OR IGNORE INTO orders VALUES (:id, :customer, :total, :status)", orders)
    print(f"Base de datos lista: {DB}")

if __name__ == "__main__":
    main()
