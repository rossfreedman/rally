# Use official Python runtime as base image
FROM python:3.11-slim

# Install system dependencies including PostgreSQL client libraries
RUN apt-get update && apt-get install -y \
    libpq-dev \
    zlib1g-dev \
    postgresql-client \
    build-essential \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies with psycopg2-binary first
RUN pip install --no-cache-dir psycopg2-binary
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8080

# Start the main Rally server directly  
CMD ["python", "server.py"]