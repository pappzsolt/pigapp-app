# HTTP-ról HTTPS-re átirányítás
server {
    listen 80;
    server_name 192.168.1.37;  # Használj domain nevet, ha szükséges
    return 301 https://$host$request_uri;
}

# HTTPS szerver
server {
    listen 443 ssl;
    server_name 192.168.1.37;

    ssl_certificate /etc/ssl/certs/selfsigned.crt;
    ssl_certificate_key /etc/ssl/private/selfsigned.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    root /vol/static;
    index index.html;

    # Statikus fájlok kiszolgálása
    location /static {
        alias /vol/static;
    }

    # Uwsgi proxy beállítása
    location / {
        uwsgi_pass           ${APP_HOST}:${APP_PORT};
        include              /etc/nginx/uwsgi_params;
        client_max_body_size 10M;
    }
}

