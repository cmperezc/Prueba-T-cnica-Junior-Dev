# Despliegue en AWS EC2 detrás de Cloudflare

```
navegador ──HTTPS──▶ Cloudflare (proxy, TLS de borde)
                         │ HTTPS · certificado de origen · SSL "Full (strict)"
                         ▼
          EC2 · security group: 80/443 solo desde IPs de Cloudflare
          nginx (:443, sirve /static, cabeceras de seguridad)
             ▼
          gunicorn (127.0.0.1:8000, 2 workers · systemd)
             ▼
          Flask → SQLite en disco EBS
```

**En línea:** <https://pymedesk.varitia.com>

En los pasos, `pedidos.tudominio.com` es el subdominio de ejemplo; en este despliegue es `pymedesk.varitia.com`.

## 1. AWS (consola web)

1. **Prefix list de Cloudflare.** Los visitantes entran por el dominio, así que al servidor solo se conecta Cloudflare. Si se aceptan únicamente sus IPs, nadie puede saltarse el proxy (ni su protección ni el HTTPS) entrando directo por la IP. Ve a VPC → *Managed prefix lists* → *Create*.
   - Nombre: `cloudflare-ipv4`.
   - Familia: IPv4.
   - Max entries: 20.
   - Entradas: los rangos de <https://www.cloudflare.com/ips-v4>.
2. **Instancia.** Ve a EC2 → *Launch instance*.
   - AMI: **Ubuntu Server 24.04 LTS**.
   - Tipo: **t3.micro**.
   - Key pair: crea uno y descarga el `.pem`.
   - Security group nuevo:

     | Tipo | Puerto | Origen |
     |---|---|---|
     | SSH | 22 | My IP |
     | HTTP | 80 | prefix list `cloudflare-ipv4` |
     | HTTPS | 443 | prefix list `cloudflare-ipv4` |

3. **IP elástica.** Ve a EC2 → *Elastic IPs* → *Allocate* y luego *Associate* a la instancia. Así la IP no cambia al detener la instancia.

## 2. Cloudflare (dashboard)

1. **DNS** → *Add record*: tipo `A`, nombre `pedidos`, IPv4 = la IP elástica, **Proxied** (nube naranja).
2. **SSL/TLS → Origin Server** → *Create certificate*.
   - Clave RSA.
   - Hostnames: `pedidos.tudominio.com`.
   - Validez: 15 años.
   - Copia el **certificado** y la **clave privada**. La clave solo se muestra una vez.
3. **SSL/TLS → Overview** → modo **Full (strict)**.
   - Si el dominio tiene otros sitios, no cambies el modo global. Crea en *Rules → Configuration Rules* una regla con `Hostname equals pedidos.tudominio.com` → SSL: *Full (strict)*.
4. **SSL/TLS → Edge Certificates** → activa **Always Use HTTPS**.

## 3. Instalar la app (SSH)

```bash
chmod 400 mi-llave.pem
ssh -i mi-llave.pem ubuntu@<IP_ELASTICA>

sudo apt update && sudo apt install -y python3-venv nginx git
sudo git clone https://github.com/cmperezc/Prueba-T-cnica-Junior-Dev.git /opt/pymedesk
sudo chown -R ubuntu:ubuntu /opt/pymedesk
cd /opt/pymedesk
python3 -m venv .venv
.venv/bin/pip install -r requirements-prod.txt
.venv/bin/python seed.py
```

## 4. Certificado de origen

```bash
sudo mkdir -p /etc/ssl/cloudflare
sudo nano /etc/ssl/cloudflare/origin.pem   # pega el certificado
sudo nano /etc/ssl/cloudflare/origin.key   # pega la clave privada
sudo chmod 600 /etc/ssl/cloudflare/origin.key
```

## 5. Servicio y nginx

```bash
sudo cp deploy/pymedesk.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now pymedesk

sudo cp deploy/nginx.conf /etc/nginx/sites-available/pymedesk
sudo ln -sf /etc/nginx/sites-available/pymedesk /etc/nginx/sites-enabled/pymedesk
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

## 6. Verificar

```bash
curl -I https://pedidos.tudominio.com                   # 200, "server: cloudflare"
curl -i -X POST https://pedidos.tudominio.com/api/orders/3/ship  # 409, pedido cancelado
curl -m 5 -I http://<IP_ELASTICA>                       # timeout: solo Cloudflare puede llegar al origen
```

## Operación

```bash
sudo systemctl status pymedesk                         # estado
sudo journalctl -u pymedesk -f                         # logs de la app
git pull && sudo systemctl restart pymedesk            # actualizar
rm data/orders.sqlite3 && .venv/bin/python seed.py     # restaurar datos de ejemplo
```

## Notas

- La app no tiene autenticación: cualquiera con la URL puede marcar pedidos como enviados. Es aceptable para una demo, pero no para producción.
- Mejoras posibles:
  - *Authenticated Origin Pulls* (mTLS entre Cloudflare y nginx).
  - `real_ip_header CF-Connecting-IP` para registrar la IP real del cliente en los logs de nginx.
- Configura una alerta en **AWS Budgets** y libera la IP elástica y termina la instancia al acabar.

## Despliegue continuo (GitHub Actions + OIDC + SSM)

Cada push a `main` ejecuta [`.github/workflows/deploy.yml`](../.github/workflows/deploy.yml):

1. GitHub obtiene **credenciales temporales** de AWS por OIDC. No hay llaves guardadas en GitHub.
2. Con **SSM Run Command**, el servidor hace `git pull` y ejecuta [`deploy/update.sh`](update.sh): dependencias, servicio, nginx y reinicio. No se abre el SSH a internet.
3. Se verifica que el sitio responda.

### Configuración (una sola vez)

1. **Rol de la instancia:** en IAM → *Roles* → *Create role*, elige *AWS service* → EC2 y la política `AmazonSSMManagedInstanceCore`, y nómbralo `pymedesk-ec2-ssm`. Luego, en EC2 → instancia → *Actions → Security → Modify IAM role*, asígnaselo.
2. **Proveedor OIDC:** en IAM → *Identity providers* → *Add provider* → OpenID Connect.
   - URL: `https://token.actions.githubusercontent.com`
   - Audience: `sts.amazonaws.com`
3. **Rol para GitHub:** en IAM → *Roles* → *Create role*, elige *Web identity* con ese proveedor y la audiencia `sts.amazonaws.com`.
   - GitHub organization: `cmperezc`
   - Repository: `Prueba-T-cnica-Junior-Dev`
   - Branch: `main`

   **Revisa el `sub` de la trust policy.** GitHub usa *sujetos inmutables* (con los IDs del dueño y del repo), y el asistente de AWS genera el formato antiguo. Consulta el prefijo real en `https://api.github.com/repos/<dueño>/<repo>/actions/oidc/customization/sub` y usa `<sub_claim_prefix>:ref:refs/heads/main` con `StringEquals`. Si no coincide, el deploy falla con `Not authorized to perform sts:AssumeRoleWithWebIdentity`.

   Nómbralo `pymedesk-github-deploy` y agrégale esta política en línea:

   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": "ssm:SendCommand",
         "Resource": [
           "arn:aws:ec2:us-east-1:<ACCOUNT_ID>:instance/<INSTANCE_ID>",
           "arn:aws:ssm:us-east-1::document/AWS-RunShellScript"
         ]
       },
       {
         "Effect": "Allow",
         "Action": ["ssm:GetCommandInvocation", "ssm:ListCommandInvocations"],
         "Resource": "*"
       }
     ]
   }
   ```
4. **Secretos del repo:** en GitHub → *Settings → Secrets and variables → Actions*, crea:
   - `AWS_ROLE_ARN`: el ARN del rol `pymedesk-github-deploy`.
   - `EC2_INSTANCE_ID`: el ID de la instancia.
