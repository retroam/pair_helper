FROM python:3.10-slim

# Set working directory
WORKDIR /workspace

# Install system dependencies (if needed for testing)
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Default command (will be overridden by docker run)
CMD ["python"]
