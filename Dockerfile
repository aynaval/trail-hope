FROM python:3.11-slim

# Set environment variables for Python and Pip
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore \
    PORT=8000 

# Set a non-root user (recommended for security)
RUN addgroup --system appgroup && adduser --system --group appuser

# Set working directory
WORKDIR /app

# Copy only requirements first to optimize caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Change ownership to non-root user
RUN chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Use dynamic port allocation
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
