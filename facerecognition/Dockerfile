FROM python:3.11-slim

WORKDIR /app

RUN apt-get update \
	&& apt-get install -y --no-install-recommends tk \
	&& rm -rf /var/lib/apt/lists/*

COPY config/requirements.txt /app/config/requirements.txt
RUN pip install --no-cache-dir -r /app/config/requirements.txt

COPY . /app

ENV PYTHONUNBUFFERED=1

EXPOSE 8787

CMD ["sh", "-c", "python scripts/app_runner.py api --host 0.0.0.0 --port ${PORT:-8787}"]
