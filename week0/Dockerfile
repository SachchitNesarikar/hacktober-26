FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY . .
ENV HOST=0.0.0.0 PORT=8765 BATON_DISABLE_REPO=1
EXPOSE 8765
CMD ["python", "-m", "baton"]
