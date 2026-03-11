FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ backend/

# Copy entrypoint
COPY start.sh .
RUN chmod +x start.sh

# Default port
ENV PORT=8000
EXPOSE 8000

ENTRYPOINT ["./start.sh"]
