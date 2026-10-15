# Despliegue en AWS EC2

Arquitectura: navegador → **nginx** (:80, sirve `/static`) → **gunicorn** (127.0.0.1:8000, 2 workers) → Flask → SQLite en disco (EBS).

## 1. Crear la instancia (consola web)

1. EC2 → **Launch instance**.
   - AMI: **Ubuntu Server 24.04 LTS**.
   - Tipo: **t3.micro**.
   - Key pair: crea uno y descarga el `.pem`.
2. Security group:
   - SSH (22) → **My IP**.
   - HTTP (80) → **Anywhere**.
3. Lanza la instancia y copia su **IPv4 pública**.

## 2. Instalar la app

```bash
chmod 400 mi-llave.pem
ssh -i mi-llave.pem ubuntu@<IP_PUBLICA>

sudo apt update && sudo apt install -y python3-venv nginx git
sudo git clone https://github.com/cmperezc/Prueba-T-cnica-Junior-Dev.git /opt/pymedesk
sudo chown -R ubuntu:ubuntu /opt/pymedesk
cd /opt/pymedesk
python3 -m venv .venv
.venv/bin/pip install -r requirements-prod.txt
.venv/bin/python seed.py
```

## 3. Servicio y proxy

```bash
sudo cp deploy/pymedesk.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now pymedesk

sudo cp deploy/nginx.conf /etc/nginx/sites-available/pymedesk
sudo ln -sf /etc/nginx/sites-available/pymedesk /etc/nginx/sites-enabled/pymedesk
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

Abre `http://<IP_PUBLICA>`.

## Operación

```bash
sudo systemctl status pymedesk                    # estado
sudo journalctl -u pymedesk -f                    # logs
git pull && sudo systemctl restart pymedesk       # actualizar
rm data/orders.sqlite3 && .venv/bin/python seed.py  # restaurar datos de ejemplo
```

## Notas

- La app no tiene autenticación: cualquiera con la URL puede marcar pedidos como enviados. Es aceptable para una demo, pero no para producción.
- Sin dominio no hay HTTPS. Con un dominio, se agrega con `certbot --nginx`.
- Configura una alerta en **AWS Budgets** y detén o termina la instancia al acabar.
