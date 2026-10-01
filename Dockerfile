# ==============================================================================
# LawLense Dockerfile
# Production-like slim image for development, testing, and demo
# Python 3.11 with system headers for mysqlclient and PyMuPDF
# ==============================================================================

FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/app:/app/backend" \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies needed for compiling mysqlclient, PyMuPDF, and healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    pkg-config \
    default-libmysqlclient-dev \
    curl \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy dependency specifications first to leverage Docker layer caching
COPY requirements.txt /app/

# Upgrade pip and install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy project source code into container
COPY . /app/

# Ensure entrypoint script is executable
RUN chmod +x /app/docker/entrypoint.sh

# Expose Django development port
EXPOSE 8000

# Set entrypoint and default command
ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["python", "backend/manage.py", "runserver", "0.0.0.0:8000"]
