FROM python:3.11-slim

WORKDIR /app/backend

RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir emergentintegrations --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/ || true

COPY . .

RUN mkdir -p /app/backend/uploads

EXPOSE 8001
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001"]
