FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the traffic generator script
COPY traffic_generator.py .

# Make the script executable
RUN chmod +x traffic_generator.py

# Create a non-root user for security
RUN useradd --create-home --shell /bin/bash trafficgen

# Create log directory and set permissions
RUN mkdir -p /app/logs && \
    chown -R trafficgen:trafficgen /app && \
    chmod -R 755 /app

# Switch to non-root user
USER trafficgen

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Default command
CMD ["python", "traffic_generator.py", "--continuous"]
