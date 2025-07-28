FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    openssh-client \
    sshpass \
    && rm -rf /var/lib/apt/lists/*

# Create application directory
WORKDIR /opt/iag5-powershell-service

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Create necessary directories
RUN mkdir -p /var/log && \
    chmod +x scripts/iag-ansible-bridge.py

# Expose service port
EXPOSE 3000

# Set environment variables
ENV FLASK_APP=scripts/iag-ansible-bridge.py
ENV PYTHONPATH=/opt/iag5-powershell-service

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000/health || exit 1

# Run the application
CMD ["python", "scripts/iag-ansible-bridge.py"]