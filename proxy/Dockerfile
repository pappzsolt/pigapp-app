FROM nginxinc/nginx-unprivileged:1-alpine

LABEL maintaner="PEZSE"

USER root
RUN mkdir -p /etc/ssl/certs /etc/ssl/private

COPY ./selfsigned.crt /etc/ssl/certs/selfsigned.crt
COPY ./selfsigned.key /etc/ssl/private/selfsigned.key

RUN chown nginx:nginx /etc/ssl/certs/selfsigned.crt /etc/ssl/private/selfsigned.key
RUN chmod 644 /etc/ssl/certs/selfsigned.crt /etc/ssl/private/selfsigned.key

COPY ./default.conf.tpl /etc/nginx/conf.d/default.conf.tpl
COPY ./uwsgi_params /etc/nginx/uwsgi_params
COPY ./run.sh /run.sh

ENV LISTEN_PORT=443
ENV APP_HOST=app
ENV APP_PORT=9000

USER root

RUN mkdir -p /vol/static
RUN chmod 755 /vol/static
RUN touch /etc/nginx/conf.d/default.conf
RUN chown nginx:nginx /etc/nginx/conf.d/default.conf
RUN chmod +x /run.sh

VOLUME /vol/static

USER nginx

CMD ["/run.sh"]




