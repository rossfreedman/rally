# Use Python 3.12 slim image as base
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=3000
ENV FLASK_ENV=production
ENV FLASK_APP=server.py
ENV WEB_CONCURRENCY=1
ENV EVENTLET_NO_GREENDNS=yes

# Create necessary directories with appropriate permissions
RUN mkdir -p data logs \
    && touch logs/server.log \
    && chown -R nobody:nogroup /app \
    && chmod -R 755 /app \
    && chmod 777 data logs logs/server.log

# Switch to non-root user
USER nobody

# Expose port from environment variable
EXPOSE ${PORT}

# Railway will override this with startCommand from railway.toml 