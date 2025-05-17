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

# Create data directory if it doesn't exist and set permissions
RUN mkdir -p data && chmod 777 data

# Create log directory
RUN mkdir -p logs && touch logs/server.log && chmod 777 logs/server.log

# Initialize the database during build
RUN python init_db.py

# Expose port from environment variable
EXPOSE ${PORT}

# Command to run the application
CMD ["python", "server.py"] 