FROM ubuntu:24.04

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    python3 \
    python-is-python3 \
    python3-pytest \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY extractor.py /app/extractor.py

RUN chmod +x /app/extractor.py

CMD ["sleep", "infinity"]