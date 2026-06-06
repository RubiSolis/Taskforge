# VPS-POO 

Sistema minimo autocontenido con FastAPI, React, MySQL, phpMyAdmin y Nginx.

## Antes de empezar (Ubuntu)
Instalacion rapida:

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-plugin
sudo usermod -aG docker $USER
newgrp docker
```

Luego abrir puertos 80 y 443 en el servidor.

## Levantar el sistema

```bash
docker compose up -d --build
```

## Clonar el repo (privado)
Repositorio: `git@github.com:cosimani/vps-poo-2026.git`

La solicitud se hace en GitHub: enviar un mensaje a `cosimani` con:
- Nombre completo
- Usuario de GitHub

Luego `cosimani` envia una invitacion al repositorio y deben aceptarla en GitHub.

Luego de recibir acceso:

```bash
git clone git@github.com:cosimani/vps-poo-2026.git
cd vps-poo-2026
```

## Accesos
- App: https://TU_IP_O_DOMINIO (acepta el certificado autofirmado)
- phpMyAdmin: https://TU_IP_O_DOMINIO/poo_phpmyadmin/

## Credenciales listas para usar
- App (login): usuario `cponce`, clave `ponceclave`
- phpMyAdmin (Basic Auth): usuario `poo`, clave `clavepoo`
- API (Basic Auth): usuario `poo`, clave `clavepoo`
- MySQL: base `vps-poo`, usuario `poo_user`, clave `poo_pass`

## Notas cortas
- El certificado es autofirmado por defecto.
- La base se inicializa con el SQL en [db/init.sql](db/init.sql).
- Swagger y llamadas a la API requieren Basic Auth (el frontend ya lo envia automaticamente).
- El token JWT se envia en el header `X-Access-Token` para no chocar con Basic Auth.
- El frontend embebe el Basic Auth al momento del build.

## Let's Encrypt (opcional)

```bash
docker compose run --rm certbot certonly \
  --webroot -w /var/www/certbot \
  -d TU_DOMINIO \
  --email TU_EMAIL \
  --agree-tos --no-eff-email

sed -i 's/USE_LETSENCRYPT=0/USE_LETSENCRYPT=1/' .env
docker compose up -d --build
```
