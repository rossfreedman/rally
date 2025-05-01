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

# Create data directory if it doesn't exist
RUN mkdir -p data

# Expose port from environment variable
EXPOSE ${PORT}

# Command to run the application
CMD gunicorn --worker-class eventlet -w 1 -b 0.0.0.0:$PORT server:app 