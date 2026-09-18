# QuantBeat API image.
# Builds the read-only game data at image-build time (fetches real TSLA data;
# falls back to synthetic if the build host has no network), then serves it.
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Bake the round data into the image. `|| true` so a network-less build still
# produces an image (prep falls back to synthetic data).
RUN python prep.py || true

# Render (and most PaaS) inject $PORT; default to 8000 for local `docker run`.
ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
