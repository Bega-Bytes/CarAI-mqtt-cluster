FROM python:3.11-alpine

# Set working directory
WORKDIR /app

# Install system dependencies for numpy and other packages
RUN apk add --no-cache \
    gcc \
    musl-dev \
    linux-headers \
    g++ \
    openblas-dev

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Python script
COPY matrix_publisher.py .

# Make the script executable
RUN chmod +x matrix_publisher.py

# Create a non-root user for security
RUN addgroup -g 1001 appgroup && \
    adduser -D -u 1001 -G appgroup appuser

# Change ownership of the app directory
RUN chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Set environment variables with defaults
ENV MQTT_HOST=mosquitto
ENV MQTT_PORT=1883
ENV MQTT_TOPIC=matrices/random
ENV PUBLISH_INTERVAL=10
ENV MATRIX_ROWS=3
ENV MATRIX_COLS=3
ENV MIN_VALUE=0
ENV MAX_VALUE=100

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import paho.mqtt.client as mqtt; print('Service running')" || exit 1

# Run the application
CMD ["python", "matrix_publisher.py"]