#!/usr/bin/env bash
# Deploy the VocabBot server to a VPS whose Caddy already serves other sites.
#
#   VPS=root@203.0.113.7 DOMAIN=vocab.example.org PROXY_NETWORK=proxy_net \
#   CADDY=proxy-caddy-1 [CADDY_SITES=/opt/caddy/conf.d] scripts/deploy_vps.sh
#
# Password recovery by e-mail: SMTP_HOST, SMTP_USER and SMTP_FROM (with SMTP_PORT, default
# 465, and SMTP_SECURITY, default ssl) name the account, and the password comes from
# SMTP_PASSWORD in the environment or in the repository's .env, never from a command line.
# Without SMTP_HOST the server keeps the SMTP settings it has.
#
# The image is built here and sent over SSH (`docker save | ssh docker load`), so the
# server holds no code. Its tag is the version and the commit, with `-dirty` for
# uncommitted changes. The domain's A record must point at the server before Caddy can
# obtain the certificate. deploy/compose.yaml is the other way: a server of its own with
# its own Caddy.
set -euo pipefail
: "${VPS:?VPS=user@host}" "${DOMAIN:?DOMAIN=vocab.example.org}"
: "${PROXY_NETWORK:?PROXY_NETWORK=the Docker network of the shared Caddy}"
: "${CADDY:?CADDY=the container of the shared Caddy}"
CADDY_SITES=${CADDY_SITES:-/opt/caddy/conf.d}
cd "$(dirname "$0")/.."

version=$(sed -n 's/^version = "\(.*\)"$/\1/p' pyproject.toml)
commit=$(git rev-parse --short HEAD)
git diff --quiet HEAD || commit="$commit-dirty"
image="vocabbot-server:$version-$commit"

echo "== image $image"
docker build -f deploy/Dockerfile -t "$image" .
docker save "$image" | gzip | ssh "$VPS" 'gunzip | docker load'

echo "== files"
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
sed "s/@DOMAIN@/$DOMAIN/" deploy/vps/vocabbot.caddy.in > "$work/vocabbot.caddy"
ssh "$VPS" 'mkdir -p /opt/vocabbot'
scp -q deploy/vps/compose.yml deploy/vps/backup.sh "$work/vocabbot.caddy" "$VPS:/opt/vocabbot/"
if [ -n "${SMTP_HOST:-}" ]; then
  password=${SMTP_PASSWORD:-}
  if [ -z "$password" ] && [ -f .env ]; then
    password=$(sed -n 's/^SMTP_PASSWORD=//p' .env | tail -1 | tr -d '\r')
    case "$password" in
      \"*\" | \'*\') password=${password:1:${#password}-2} ;;
    esac
  fi
  : "${password:?SMTP_PASSWORD is not set and .env has none}"
  # docker compose fills in $NAME in an env file, except inside single quotes; a value
  # with a single quote of its own goes unquoted with every $ doubled instead
  envline() {
    case "$2" in
      *\'*) printf '%s=%s\n' "$1" "${2//\$/\$\$}" ;;
      *) printf "%s='%s'\n" "$1" "$2" ;;
    esac
  }
  (
    umask 077
    {
      envline VOCABBOT_SERVER_SMTP_HOST "$SMTP_HOST"
      envline VOCABBOT_SERVER_SMTP_PORT "${SMTP_PORT:-465}"
      envline VOCABBOT_SERVER_SMTP_USER "${SMTP_USER:?SMTP_USER}"
      envline VOCABBOT_SERVER_SMTP_PASSWORD "$password"
      envline VOCABBOT_SERVER_SMTP_FROM "${SMTP_FROM:-$SMTP_USER}"
      envline VOCABBOT_SERVER_SMTP_SECURITY "${SMTP_SECURITY:-ssl}"
    } > "$work/smtp.env"
  )
  scp -q "$work/smtp.env" "$VPS:/opt/vocabbot/smtp.env"
  ssh "$VPS" 'chmod 600 /opt/vocabbot/smtp.env'
  echo "SMTP: $SMTP_USER at $SMTP_HOST:${SMTP_PORT:-465} (${SMTP_SECURITY:-ssl})"
fi

ssh "$VPS" "VOCABBOT_IMAGE='$image' VOCABBOT_DOMAIN='$DOMAIN' VOCABBOT_PROXY_NETWORK='$PROXY_NETWORK' CADDY='$CADDY' CADDY_SITES='$CADDY_SITES' bash -s" < deploy/vps/remote.sh

echo "== https://$DOMAIN/health"
for _ in $(seq 1 30); do
  if curl -sf "https://$DOMAIN/health"; then
    echo
    exit 0
  fi
  sleep 3
done
echo "https://$DOMAIN/health does not answer yet: check the A record and the Caddy log" >&2
exit 1
