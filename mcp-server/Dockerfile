# ActionFlow MCP Server Dockerfile
# Lightweight Python image for MCP Tool Server

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY server.py .
COPY tools/ ./tools/

# Environment variables (can be overridden)
ENV BACKEND_URL=http://backend:8000
ENV MCP_PORT=3000
ENV LOG_LEVEL=INFO
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000/health || exit 1

# Run server
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "3000"]