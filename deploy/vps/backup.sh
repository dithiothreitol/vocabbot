#!/bin/sh
# A daily copy of the VocabBot data, kept for 14 days in /opt/vocabbot/backups:
# a consistent copy of accounts.db (SQLite's backup) and the learners' folders.
set -eu
cd /opt/vocabbot
mkdir -p backups
stamp=$(date +%F)
docker exec vocabbot-app python -c "
import sqlite3
source = sqlite3.connect('/data/accounts.db')
target = sqlite3.connect('/data/accounts.backup.db')
source.backup(target)
target.close()
source.close()
"
if [ -d data/learners ]; then
  tar -czf "backups/vocabbot-$stamp.tgz" -C data accounts.backup.db learners
else
  tar -czf "backups/vocabbot-$stamp.tgz" -C data accounts.backup.db
fi
rm -f data/accounts.backup.db
find backups -name 'vocabbot-*.tgz' -mtime +14 -delete
echo "$(date -Is) backup vocabbot-$stamp.tgz"
