#!/bin/bash
set -e

echo "=========================================="
echo "  MediSebi Frontend — Starting..."
echo "=========================================="

echo "  API Base URL: ${VITE_API_BASE_URL:-/api/v1}"
echo "=========================================="

# Development: use Vite dev server with proxy
if [ "${NODE_ENV}" != "production" ]; then
    echo "  Starting development server..."
    exec npx vite --host 0.0.0.0 --port 5173
else
    echo "  Starting production server..."
    # Just serve static files
    exec npx serve -s dist -l 3000
fi
