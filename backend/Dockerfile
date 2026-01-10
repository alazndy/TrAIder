# Python 3.11 Slim Image (More modern, fixes dependency issues)
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (Git is required for pandas_ta)
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Copy requirements first (caching layer)
COPY requirements.txt .

# Upgrade pip to ensure latest wheel support
RUN pip install --upgrade pip

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all files
COPY . .

# Set environment variables
# PYTHONUNBUFFERED=1 ensures logs are visible in Cloud Logging immediately
ENV PYTHONUNBUFFERED=1

# Run the FastAPI server (Render sets $PORT automatically)
CMD ["python", "main.py"]
