FROM python:3.11-slim

WORKDIR /app

# System packages (poppler for Docling, libgomp/libgl for PaddleOCR, Korean fonts, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    poppler-utils \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# supervisord configuration
COPY supervisord.conf /etc/supervisor/conf.d/nexus.conf

CMD ["supervisord", "-c", "/etc/supervisor/conf.d/nexus.conf"]
