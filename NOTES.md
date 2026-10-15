# Notas de la solución

## Problemas encontrados

1. **Se podía enviar un pedido cancelado.** `POST /api/orders/<id>/ship` solo rechazaba los pedidos ya enviados.
2. **Los fallos no se mostraban.** Si el servidor respondía con error o no había conexión, el botón se reactivaba sin explicar nada.
3. **Condición de carrera.** El endpoint leía el estado y luego actualizaba en dos consultas separadas, así que dos peticiones simultáneas podían enviar el mismo pedido.
4. **Conexiones sin cerrar.** `with sqlite3.connect(...)` solo hace commit o rollback; no cierra la conexión.
5. **Errores de base de datos silenciosos.** Sin ejecutar `seed.py`, `sqlite3.connect` creaba un archivo vacío y la API respondía 500 sin dejar rastro en los logs.
6. **Detalles de interfaz.** `/favicon.ico` daba 404 en cada carga, y el contador de pedidos quedaba con un valor viejo si fallaba la recarga.

## Cambios

- **Backend (`app.py`):** la regla es que solo se pasa de `pendiente` a `enviado`. La actualización es atómica (`UPDATE ... WHERE id = ? AND status = 'pendiente'`). Si no cambia ninguna fila, se responde 404 o 409 con un mensaje claro. `connect()` ahora cierra la conexión siempre y abre la base en modo `rw`, sin crearla si no existe. Los errores de SQLite se registran en el log, y `python app.py` avisa si falta ejecutar `seed.py`.
- **Frontend (`index.html`, `style.css`):** aviso visible con `aria-live` que muestra el mensaje del servidor, uno propio si no hay conexión, y una confirmación cuando el envío sale bien. El botón muestra "Enviando…" mientras se procesa y solo está activo en pedidos pendientes. Aun así, el servidor sigue siendo quien valida.

## Cómo lo comprobé

- **API:** pedido cancelado → 409 y sigue cancelado. Pendiente → 200 y queda enviado. Repetido → 409. Inexistente → 404. Con 10 peticiones simultáneas al mismo pedido → un 200 y nueve 409.
- **Interfaz (Chromium con Playwright, escritorio y 390 px):** aviso de éxito, aviso de error del servidor, red caída simulada y error 500 con HTML simulado. Sin errores de JavaScript en consola.
- **Manual:**
  ```bash
  curl -i -X POST http://127.0.0.1:5000/api/orders/3/ship   # 409, sigue cancelado
  ```

## Despliegue

**En línea:** <https://pymedesk.varitia.com>

AWS EC2 (Ubuntu 24.04) con nginx, gunicorn y SQLite, detrás de Cloudflare con SSL *Full (strict)* y certificado de origen. El security group solo acepta tráfico web desde las IPs de Cloudflare. Los pasos están en [`deploy/README.md`](deploy/README.md).

**Modo demo:** como el sitio es público, con `DEMO_MODE=1` (solo activado en el servidor) aparece el botón "Restaurar datos de ejemplo" y el endpoint `POST /api/demo/reset`, que recarga `data/orders.json`. En local no existen: el endpoint responde 404.

## Pendiente / con más tiempo

- **Tests automáticos** con pytest y el `test_client` de Flask para las transiciones de estado.
- **Producción real:** autenticación (hoy cualquiera con la URL puede enviar pedidos), Postgres (RDS) si hay varias instancias, y guardar la clave del certificado en AWS Secrets Manager o Parameter Store.
