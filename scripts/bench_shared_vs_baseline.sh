#!/bin/bash
set -u
MODE=${1:-shared}
PORT=9099
case "$MODE" in
  shared) ENV="AISTUDIO_SHARED_BROWSER=1 AISTUDIO_REPLAY_MODE=http";;
  legacy) ENV="";;
  *) echo "mode must be shared|legacy"; exit 1;;
esac

pkill -9 -f "main.py server" 2>/dev/null
sleep 3
cd ~/Developer/work/AIGC/aistudio-api
source .venv/bin/activate
eval "$ENV AISTUDIO_API_KEY=k AISTUDIO_PROXY=http://127.0.0.1:6152 \
  HTTPS_PROXY=http://127.0.0.1:6152 HTTP_PROXY=http://127.0.0.1:6152 \
  nohup python main.py server --port $PORT > /tmp/bench-${MODE}.log 2>&1 &"
sleep 15

for aid in $(ls data/accounts | grep "^acc_" | head -3); do
  curl -sS -X POST http://localhost:${PORT}/accounts/${aid}/activate \
    -H "Authorization: Bearer k" -o /dev/null -w "activate ${aid}: %{http_code} time=%{time_total}s\n"
  sleep 2
done

sleep 5
RSS=$(ps -axm -o rss,command 2>/dev/null | grep -E "[Cc]hromium" | grep -v grep \
  | awk '{sum+=$1} END {printf "%.0f", sum/1024}')
echo "MODE=$MODE total chromium RSS = ${RSS} MB"
pkill -9 -f "main.py server"
