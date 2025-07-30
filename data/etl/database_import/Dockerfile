# Use Python 3.11 alpine image for smaller size and better reliability
FROM python:3.11-alpine

# Set working directory
WORKDIR /app

# Install system dependencies for Alpine
RUN apk add --no-cache gcc musl-dev libffi-dev

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the ETL scripts
COPY *.py ./

# Copy runtime.txt
COPY runtime.txt ./

# Copy required modules from project root
COPY ../../../database_config.py ./
COPY ../../../database_utils.py ./
COPY ../../../config.py ./
COPY ../../../utils/ ./utils/
COPY ../../../app/ ./app/

# Create logs directory
RUN mkdir -p logs

# Set default command
CMD ["python", "master_import.py", "--league", "aptachicago"] 