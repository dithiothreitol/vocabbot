#!/bin/bash
# Runs on the server from scripts/deploy_vps.sh, in /opt/vocabbot. Other projects are never
# restarted; the shared Caddy only reloads a validated configuration, and an invalid one
# brings back the previous state.
set -euo pipefail
: "${VOCABBOT_IMAGE:?}" "${VOCABBOT_DOMAIN:?}" "${VOCABBOT_PROXY_NETWORK:?}" "${CADDY:?}" "${CADDY_SITES:?}"
cd /opt/vocabbot
chmod 644 compose.yml vocabbot.caddy
chmod 755 backup.sh
mkdir -p data backups
chown 10001:10001 data

umask 077
cat > .env <<EOF
VOCABBOT_IMAGE=$VOCABBOT_IMAGE
VOCABBOT_DOMAIN=$VOCABBOT_DOMAIN
VOCABBOT_PROXY_NETWORK=$VOCABBOT_PROXY_NETWORK
VOCABBOT_TIMEZONE=${VOCABBOT_TIMEZONE:-Europe/Warsaw}
EOF
umask 022

echo "== container"
docker compose up -d --remove-orphans
for _ in $(seq 1 30); do
  if docker exec vocabbot-app python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)" 2>/dev/null; then
    break
  fi
  sleep 2
done
docker exec vocabbot-app python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).read().decode())"

echo "== Caddy site"
site="$CADDY_SITES/vocabbot.caddy"
rm -f /root/vocabbot.caddy.prev
[ -f "$site" ] && cp "$site" /root/vocabbot.caddy.prev
cp vocabbot.caddy "$site"
if docker exec "$CADDY" caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile >/tmp/vocabbot-caddy.log 2>&1; then
  docker exec "$CADDY" caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile
  echo "Caddy reloaded with vocabbot.caddy"
else
  tail -20 /tmp/vocabbot-caddy.log >&2
  if [ -f /root/vocabbot.caddy.prev ]; then mv /root/vocabbot.caddy.prev "$site"; else rm -f "$site"; fi
  echo "Caddy configuration invalid: previous state restored, Caddy not reloaded" >&2
  exit 1
fi
docker exec "$CADDY" wget -qO- http://vocabbot-app:8000/health
echo " (from the shared Caddy)"

echo "== backup"
line="0 4 * * * /opt/vocabbot/backup.sh >> /opt/vocabbot/backups/backup.log 2>&1"
if ! crontab -l 2>/dev/null | grep -qF "/opt/vocabbot/backup.sh"; then
  (crontab -l 2>/dev/null; echo "$line") | crontab -
  echo "cron: daily backup at 4:00"
fi
