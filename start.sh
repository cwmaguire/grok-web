#!/bin/bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Cleanup on exit
cleanup() {
    echo ""
    echo "Shutting down..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    wait $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    echo "Done."
}
trap cleanup EXIT INT TERM

# Start backend
echo "Starting backend..."
cd "$DIR/backend"
uv run uvicorn grok_web.main:app --reload --port 8111 &
BACKEND_PID=$!

# Start frontend
echo "Starting frontend..."
cd "$DIR/frontend"
npx vite --port 5173 &
FRONTEND_PID=$!

echo ""
echo "grok-web running:"
echo "  Frontend: http://localhost:5173"
echo "  Backend:  http://localhost:8111"
echo ""
echo "Press Ctrl+C to stop."

wait
