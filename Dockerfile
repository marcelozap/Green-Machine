# GREEN MACHINE — single container: built Pilot UI + FastAPI Engine on port 8000
FROM node:22-bookworm-slim AS pilot_build
WORKDIR /repo
COPY pilot/package.json pilot/package-lock.json* ./pilot/
WORKDIR /repo/pilot
RUN npm install
COPY pilot/ ./
RUN npm run build

FROM python:3.12-slim-bookworm
WORKDIR /app
ENV PYTHONUNBUFFERED=1
RUN mkdir -p /app/data
RUN pip install --no-cache-dir --upgrade pip
COPY engine/requirements.txt /app/engine/requirements.txt
RUN pip install --no-cache-dir -r /app/engine/requirements.txt
COPY engine/ /app/engine/
COPY historian/ /app/historian/
COPY --from=pilot_build /repo/engine/static/cockpit /app/engine/app/static/cockpit
WORKDIR /app/engine
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
