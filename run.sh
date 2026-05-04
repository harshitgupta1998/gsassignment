#!/usr/bin/env bash
# Small helper to run backend extraction and start a static frontend server
set -eu

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
MODE="hybrid"
PORT=8000

usage() {
  cat <<-USAGE
Usage: $0 [--mode hybrid|llm|deterministic] [--port PORT]

Defaults: --mode hybrid --port 8000

This script runs:
  1) python3 backend/extract.py --mode <mode>
  2) python3 -m http.server <port> (serving the repository root so /frontend/ and backend/output are available)

It writes the server PID to .server.pid in the repository root.
Use 'kill \\$(cat .server.pid)' to stop the server.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode)
      MODE="$2"
      shift 2
      ;;
    --port)
      PORT="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown arg: $1" >&2
      usage
      exit 2
      ;;
  esac
done

# If a .env file exists in the repo root, source it so environment variables like OPENAI_API_KEY are available.
if [ -f "$ROOT_DIR/.env" ]; then
  echo "Sourcing .env from $ROOT_DIR/.env"
  # Export all variables in .env for child processes
  set -a
  # shellcheck disable=SC1090
  . "$ROOT_DIR/.env"
  set +a
fi

echo "Running extractor (mode=$MODE) ..."
python3 "$ROOT_DIR/backend/extract.py" --mode "$MODE"

echo "Checking port $PORT ..."
if lsof -i :${PORT} -sTCP:LISTEN -n -P >/dev/null 2>&1; then
  echo "Port ${PORT} is already in use. Choose another port or stop the process using it." >&2
  exit 3
fi

echo "Starting static server on port ${PORT} (serving ${ROOT_DIR}) ..."
nohup python3 -m http.server "${PORT}" >/dev/null 2>&1 &
PID=$!
# Try to write the PID; if that fails, print the PID so the user can capture it.
if echo "${PID}" > "${ROOT_DIR}/.server.pid" 2>/dev/null; then
  echo "Server started with PID ${PID} (pid written to ${ROOT_DIR}/.server.pid). Open http://localhost:${PORT}/frontend/"
else
  echo "Server started with PID ${PID} (could not write ${ROOT_DIR}/.server.pid). Open http://localhost:${PORT}/frontend/"
fi

exit 0
