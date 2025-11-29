FROM python:3.9-slim

# Python ne puffereljen (logok azonnal látszanak)
ENV PYTHONUNBUFFERED=1

# Munkakönyvtár
WORKDIR /app

# Követelmények és kód másolása
COPY ./requirements.txt /tmp/requirements.txt
COPY ./app /app
COPY ./scripts /scripts

# Virtuális környezet + csomagok telepítése
RUN python -m venv /py \
    && /py/bin/pip install --upgrade pip \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential \
       libpq-dev \
       libjpeg-dev \
       zlib1g-dev \
    && /py/bin/pip install -r /tmp/requirements.txt \
    && rm -rf /var/lib/apt/lists/* /tmp

# Django user + volume-ok
RUN adduser --disabled-password --no-create-home django-user \
    && mkdir -p /vol/web/media \
    && mkdir -p /vol/web/static \
    && chown -R django-user:django-user /vol \
    && chmod -R 755 /vol \
    && chmod -R +x /scripts

# PATH-be tesszük a venv-et és a scripteket
ENV PATH="/scripts:/py/bin:$PATH"

# Nem root userrel futunk
USER django-user

# uWSGI port
EXPOSE 9000

# Indító script
CMD ["run.sh"]

