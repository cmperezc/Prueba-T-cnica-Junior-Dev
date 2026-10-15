import pytest
import app as app_module
import seed


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Base temporal por test: no toca data/orders.sqlite3.
    db = tmp_path / "orders.sqlite3"
    monkeypatch.setattr(seed, "DB", db)
    monkeypatch.setattr(app_module, "DB", db)
    seed.main()
    return app_module.app.test_client()


def status_of(client, order_id):
    return next(o["status"] for o in client.get("/api/orders").get_json() if o["id"] == order_id)


def test_lista_pedidos(client):
    res = client.get("/api/orders")
    assert res.status_code == 200
    assert len(res.get_json()) == 8


def test_envia_pedido_pendiente(client):
    res = client.post("/api/orders/1/ship")
    assert res.status_code == 200
    assert res.get_json()["status"] == "enviado"
    assert status_of(client, 1) == "enviado"


def test_rechaza_pedido_cancelado(client):
    res = client.post("/api/orders/3/ship")
    assert res.status_code == 409
    assert res.get_json()["error"] == "No se puede enviar un pedido cancelado."
    assert status_of(client, 3) == "cancelado"


def test_rechaza_pedido_ya_enviado(client):
    assert client.post("/api/orders/2/ship").status_code == 409
    assert status_of(client, 2) == "enviado"


def test_pedido_inexistente(client):
    assert client.post("/api/orders/999/ship").status_code == 404


def test_sin_base_de_datos(tmp_path, monkeypatch):
    # mode=rw: responde 500 con mensaje claro y no crea una base vacía.
    db = tmp_path / "no-existe.sqlite3"
    monkeypatch.setattr(app_module, "DB", db)
    res = app_module.app.test_client().get("/api/orders")
    assert res.status_code == 500
    assert "error" in res.get_json()
    assert not db.exists()


def test_reset_desactivado_fuera_de_demo(client):
    assert client.post("/api/demo/reset").status_code == 404


def test_reset_restaura_datos(client, monkeypatch):
    monkeypatch.setattr(app_module, "DEMO_MODE", True)
    client.post("/api/orders/1/ship")
    assert client.post("/api/demo/reset").status_code == 200
    assert status_of(client, 1) == "pendiente"
