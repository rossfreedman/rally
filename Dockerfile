# Use official Python runtime as base image
FROM python:3.11-alpine

# Install system dependencies including PostgreSQL client libraries
RUN apk add --no-cache \
    postgresql-dev \
    zlib-dev \
    postgresql-client \
    build-base \
    pkg-config

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Upgrade pip first to avoid issues
RUN pip install --upgrade pip

# Install Python dependencies with improved error handling
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install --no-cache-dir --timeout=300 --retries=5 psycopg2-binary
RUN pip install --no-cache-dir --timeout=300 --retries=5 -r requirements.txt

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8080

# Start the main Rally server directly  
CMD ["python", "server.py"]