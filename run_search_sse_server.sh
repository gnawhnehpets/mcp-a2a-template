#!/bin/bash

# Exit on error
set -e

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
  source .venv/bin/activate
fi

# Set PYTHONPATH to project root and run the server
PYTHONPATH="$(pwd)" python3 mcp_server/shttp/mcp_shttp_search_google.py "$@"
