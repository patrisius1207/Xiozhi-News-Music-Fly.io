# Dockerfile untuk Railway
FROM python:3.11-slim

# Install ffmpeg (dibutuhkan yt-dlp untuk audio extraction)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy semua file
COPY . .

# Download mcp_pipe.py dari repo resmi
RUN python -c "\
import urllib.request; \
urllib.request.urlretrieve(\
'https://github.com/78/mcp-calculator/raw/refs/heads/main/mcp_pipe.py',\
'mcp_pipe.py'\
)"

# Jalankan MCP pipe
CMD ["python", "mcp_pipe.py"]
