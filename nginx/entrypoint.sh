#!/bin/sh
set -e

CERT_DIR=/etc/nginx/certs
CRT=${CERT_DIR}/selfsigned.crt
KEY=${CERT_DIR}/selfsigned.key
DOMAIN=${NGINX_SERVER_NAME:-localhost}
LE_CERT=/etc/letsencrypt/live/${DOMAIN}/fullchain.pem
LE_KEY=/etc/letsencrypt/live/${DOMAIN}/privkey.pem

TEMPLATE=/etc/nginx/templates/nginx.selfsigned.conf

if [ "${USE_LETSENCRYPT}" = "1" ] && [ -f "$LE_CERT" ] && [ -f "$LE_KEY" ]; then
  TEMPLATE=/etc/nginx/templates/nginx.letsencrypt.conf
else
  if [ ! -f "$CRT" ] || [ ! -f "$KEY" ]; then
    mkdir -p "$CERT_DIR"
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
      -keyout "$KEY" \
      -out "$CRT" \
      -subj "/C=AR/ST=BA/L=CABA/O=VPS-POO/OU=DEV/CN=${DOMAIN}"
  fi
fi

envsubst '${NGINX_SERVER_NAME}' < "$TEMPLATE" > /etc/nginx/nginx.conf

exec nginx -g "daemon off;"
