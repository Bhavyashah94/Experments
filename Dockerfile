# ── Stage 1: Build Modern Vue 3 Frontend ──────────────────────────────────
FROM node:26-alpine AS frontend-builder
WORKDIR /build

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# ── Stage 2: Production Python Runner (Non-Root UID 1000) ──────────────────
FROM python:3.10-slim

# Oracle Cloud VM / Hugging Face Spaces runs as user with UID 1000
RUN useradd -m -u 1000 user

WORKDIR /app

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY --chown=user:user . .
COPY --from=frontend-builder --chown=user:user /build/dist ./frontend/dist

# Create uploads, output, and data directories with appropriate permissions
RUN mkdir -p /app/uploads /app/output /app/data && chown -R user:user /app

# Switch to non-root user
USER user

# Reverse-proxied port 7860
EXPOSE 7860

# Run Gunicorn on port 7860 with 120s timeout
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:7860", "--workers", "2", "--threads", "4", "--timeout", "120"]
