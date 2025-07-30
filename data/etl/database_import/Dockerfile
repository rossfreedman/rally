# Use Python 3.11 slim image for smaller size
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the ETL scripts
COPY *.py ./

# Copy runtime.txt
COPY runtime.txt ./

# Create logs directory
RUN mkdir -p logs

# Set default command
CMD ["python", "master_import.py", "--league", "aptachicago"] 