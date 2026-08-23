# SAWALA backend + dashboard, for deployment where the host has no local
# display (e.g. Biznet Gio Cloud) - screen capture then comes from the
# browser's own getDisplayMedia() via /api/ingest/screen instead of the
# local mss-based capture used by the desktop build.
FROM python:3.12-slim AS backend-deps

# opencv/mediapipe need these even though we never open a GUI window here
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM node:20-slim AS dashboard-build
WORKDIR /dashboard
COPY dashboard/package.json dashboard/package-lock.json ./
RUN npm ci
COPY dashboard/ ./
RUN npm run build

FROM backend-deps AS final
WORKDIR /app

COPY src/ ./src/
COPY config.cloud.yaml ./config.yaml
COPY --from=dashboard-build /dashboard/dist ./dashboard/dist

# capture.enable_local_capture must be false in this image's config.yaml -
# there is no display in the container, only browser-pushed frames via
# /api/ingest/screen work here.
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["python", "-m", "src.api.main"]
