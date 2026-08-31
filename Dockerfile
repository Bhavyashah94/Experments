# ── Stage 1: Build Modern Vue 3 Frontend ──────────────────────────────────
FROM node:20-alpine AS frontend-builder
WORKDIR /build

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# ── Stage 2: Production Python Runner (Non-Root UID 1000) ──────────────────
FROM python:3.10-slim

# Hugging Face Spaces runs as user with UID 1000
RUN useradd -m -u 1000 user

WORKDIR /app

# Install system dependencies for PyMuPDF & Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY --chown=user:user . .

# Copy compiled frontend distribution from Stage 1 into frontend/dist
COPY --from=frontend-builder --chown=user:user /build/dist ./frontend/dist

# Create uploads & output directories with appropriate permissions
RUN mkdir -p /app/uploads /app/output && chown -R user:user /app

# Switch to non-root user
USER user

# Hugging Face Spaces port 7860
EXPOSE 7860

# Run Gunicorn on port 7860 with 120s timeout
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:7860", "--workers", "2", "--threads", "4", "--timeout", "120"]
