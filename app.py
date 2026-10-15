from contextlib import contextmanager
from pathlib import Path
import sqlite3
from flask import Flask, jsonify, render_template

DB = Path(__file__).resolve().parent / "data" / "orders.sqlite3"
app = Flask(__name__)

@contextmanager
def connect():
    # mode=rw: no crea una base vacía si falta ejecutar seed.py.
    con = sqlite3.connect(f"{DB.as_uri()}?mode=rw", uri=True)
    con.row_factory = sqlite3.Row
    try:
        with con:  # commit o rollback
            yield con
    finally:
        con.close()

@app.get("/")
def index():
    return render_template("index.html")

@app.get("/api/orders")
def orders():
    try:
        with connect() as con:
            return jsonify([dict(row) for row in con.execute("SELECT * FROM orders ORDER BY id")])
    except sqlite3.Error:
        app.logger.exception("Error al cargar los pedidos")
        return jsonify(error="No se pudieron cargar los pedidos."), 500

@app.post("/api/orders/<int:order_id>/ship")
def ship(order_id):
    try:
        with connect() as con:
            # Actualización condicional: solo cambia si sigue pendiente, evitando condiciones de carrera.
            cur = con.execute(
                "UPDATE orders SET status = 'enviado' WHERE id = ? AND status = 'pendiente'", (order_id,)
            )
            row = con.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        if cur.rowcount == 1:
            return jsonify(dict(row))
        if row is None:
            return jsonify(error="Pedido no encontrado."), 404
        if row["status"] == "enviado":
            return jsonify(error="El pedido ya está enviado."), 409
        if row["status"] == "cancelado":
            return jsonify(error="No se puede enviar un pedido cancelado."), 409
        return jsonify(error="Solo los pedidos pendientes se pueden enviar."), 409
    except sqlite3.Error:
        app.logger.exception("Error al enviar el pedido %s", order_id)
        return jsonify(error="No se pudo actualizar el pedido."), 500

if __name__ == "__main__":
    if not DB.exists():
        raise SystemExit("No existe la base de datos. Ejecuta primero: python seed.py")
    app.run(debug=True)
