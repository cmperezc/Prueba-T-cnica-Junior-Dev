from pathlib import Path
import sqlite3
from flask import Flask, jsonify, render_template

DB = Path(__file__).resolve().parent / "data" / "orders.sqlite3"
app = Flask(__name__)

def connect():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con

@app.get("/")
def index():
    return render_template("index.html")

@app.get("/api/orders")
def orders():
    try:
        with connect() as con:
            return jsonify([dict(row) for row in con.execute("SELECT * FROM orders ORDER BY id")])
    except sqlite3.Error:
        return jsonify(error="No se pudieron cargar los pedidos."), 500

@app.post("/api/orders/<int:order_id>/ship")
def ship(order_id):
    try:
        with connect() as con:
            row = con.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
            if row is None:
                return jsonify(error="Pedido no encontrado."), 404
            if row["status"] == "enviado":
                return jsonify(error="El pedido ya está enviado."), 409
            if row["status"] == "cancelado":
                return jsonify(error="No se puede enviar un pedido cancelado."), 409
            if row["status"] != "pendiente":
                return jsonify(error="Solo los pedidos pendientes se pueden enviar."), 409
            con.execute("UPDATE orders SET status = 'enviado' WHERE id = ?", (order_id,))
            updated = con.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        return jsonify(dict(updated))
    except sqlite3.Error:
        return jsonify(error="No se pudo actualizar el pedido."), 500

if __name__ == "__main__":
    app.run(debug=True)
