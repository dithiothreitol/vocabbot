#!/usr/bin/env bash
# Deploy the VocabBot server to a VPS whose Caddy already serves other sites.
#
#   VPS=root@203.0.113.7 DOMAIN=vocab.example.org PROXY_NETWORK=proxy_net \
#   CADDY=proxy-caddy-1 [CADDY_SITES=/opt/caddy/conf.d] scripts/deploy_vps.sh
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
