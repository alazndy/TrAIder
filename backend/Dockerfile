# Python 3.9 Slim Image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy requirements first (caching layer)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all files
COPY . .

# Set environment variables
# PYTHONUNBUFFERED=1 ensures logs are visible in Cloud Logging immediately
ENV PYTHONUNBUFFERED=1

# Run the FastAPI server (Render sets $PORT automatically)
CMD ["python", "main.py"]
