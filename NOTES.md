# Notas de la solución

## Problemas encontrados

1. **Se podía enviar un pedido cancelado.** `POST /api/orders/<id>/ship` solo rechazaba los pedidos ya enviados.
2. **Los fallos no se mostraban.** Si el servidor respondía con error o no había conexión, el botón se reactivaba sin explicar nada.
3. **Condición de carrera.** El endpoint leía el estado y luego actualizaba en dos consultas separadas, así que dos peticiones simultáneas podían enviar el mismo pedido.
4. **Conexiones sin cerrar.** `with sqlite3.connect(...)` solo hace commit o rollback; no cierra la conexión.

## Cambios

- **Backend (`app.py`):** la regla es que solo se pasa de `pendiente` a `enviado`. La actualización es atómica (`UPDATE ... WHERE id = ? AND status = 'pendiente'`). Si no cambia ninguna fila, se responde 404 o 409 con un mensaje claro. `connect()` ahora cierra la conexión siempre.
- **Frontend (`index.html`, `style.css`):** aviso visible con `aria-live` que muestra el mensaje del servidor, uno propio si no hay conexión, y una confirmación cuando el envío sale bien. El botón muestra "Enviando…" mientras se procesa y solo está activo en pedidos pendientes. Aun así, el servidor sigue siendo quien valida.

## Cómo lo comprobé

- **API:** pedido cancelado → 409 y sigue cancelado. Pendiente → 200 y queda enviado. Repetido → 409. Inexistente → 404. Con 10 peticiones simultáneas al mismo pedido → un 200 y nueve 409.
- **Interfaz (Chromium con Playwright, escritorio y 390 px):** aviso de éxito, aviso de error del servidor, red caída simulada y error 500 con HTML simulado. Sin errores de JavaScript en consola.
- **Manual:**
  ```bash
  curl -i -X POST http://127.0.0.1:5000/api/orders/3/ship   # 409, sigue cancelado
  ```

## Despliegue

Desplegado en AWS EC2 con nginx, gunicorn y SQLite. Los pasos están en [`deploy/README.md`](deploy/README.md).

## Pendiente / con más tiempo

- **Base de datos inexistente:** si no se ejecuta `seed.py`, `sqlite3.connect` crea un archivo vacío y la API responde "No se pudieron cargar los pedidos". Propuesta: validar al arrancar y mostrar "Ejecuta `python seed.py`".
- **Tests automáticos** con pytest y el `test_client` de Flask para las transiciones de estado.
- **Producción:** gunicorn en lugar del servidor de desarrollo (sin `debug=True`), y Postgres si hay varias instancias.
