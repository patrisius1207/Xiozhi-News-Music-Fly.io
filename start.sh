#!/bin/bash
# Jalankan Audio Stream Server di port 8080
# Sekaligus handle health check & MCP keepalive
python stream_server.py &

# Jalankan MCP pipe (proses utama)
python mcp_pipe.py
