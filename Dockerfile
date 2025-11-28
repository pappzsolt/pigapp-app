FROM python:3.9.20-alpine
ENV PYTHONBUFFERED 1
COPY ./requirements.txt /tmp/requirements.txt
COPY ./app /app
COPY ./scripts /scripts
WORKDIR /app
EXPOSE 9000

RUN python -m venv /py
RUN /py/bin/pip install --upgrade pip
RUN apk add --update --no-cache postgresql-client jpeg-dev
RUN apk add --update --no-cache --virtual .tmp-build-deps build-base postgresql-dev musl-dev linux-headers
RUN /py/bin/pip install -r /tmp/requirements.txt
RUN rm -rf /tmp
RUN apk del .tmp-build-deps
RUN adduser --disabled-password --no-create-home django-user
RUN mkdir -p /vol/web/media
RUN mkdir -p /vol/web/static
RUN chown -R django-user:django-user /vol
RUN chmod -R 755 /vol
RUN chmod -R +x /scripts
ENV PATH="/scripts:/py/bin:$PATH"
USER django-user

CMD ["run.sh"]
