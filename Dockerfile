FROM python:3.11-alpine

WORKDIR /app

# Install system dependencies (Alpine style)
RUN apk add --no-cache \
    gcc \
    musl-dev \
    postgresql-dev \
    postgresql-client \
    linux-headers

# Upgrade pip
RUN pip install --upgrade pip

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Create uploads directory for media files
RUN mkdir -p /app/uploads

# Expose FastAPI port
EXPOSE 8000

# Run FastAPI app (Railway provides PORT env var)
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}