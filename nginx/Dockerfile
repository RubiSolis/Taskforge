FROM nginx:1.27-alpine

RUN apk add --no-cache openssl gettext

COPY templates /etc/nginx/templates
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
