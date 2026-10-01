#!/bin/bash
set -e

echo "============================================================"
echo "LawLense Container Startup Initialization"
echo "============================================================"

# Ensure data directories exist
mkdir -p data/processed data/raw

# -------------------------------------------------------------
# 1. Check whether data/processed/bns_sections.json exists
# -------------------------------------------------------------
if [ ! -f "data/processed/bns_sections.json" ]; then
    echo "[Pipeline] data/processed/bns_sections.json not found."
    if [ ! -f "data/raw/BNS.pdf" ]; then
        echo "[Pipeline ERROR] data/raw/BNS.pdf is missing! Cannot ingest corpus." >&2
        exit 1
    fi
    echo "[Pipeline] Step 1/2: Extracting raw text from data/raw/BNS.pdf..."
    python scripts/ingest.py

    echo "[Pipeline] Step 2/2: Preprocessing raw text into sections JSON..."
    python scripts/preprocess.py
    echo "[Pipeline] Corpus extraction & preprocessing complete."
else
    echo "[Pipeline] Verified data/processed/bns_sections.json exists."
fi

# -------------------------------------------------------------
# 2. Check whether embeddings and metadata exist
# -------------------------------------------------------------
if [ ! -f "data/processed/bns_embeddings.npz" ] || [ ! -f "data/processed/bns_metadata.json" ]; then
    echo "[Embeddings] Vector embeddings or metadata missing."
    echo "[Embeddings] Generating multilingual-e5-base embeddings from bns_sections.json..."
    python scripts/embed.py
    echo "[Embeddings] Embedding generation complete."
else
    echo "[Embeddings] Verified bns_embeddings.npz and bns_metadata.json exist."
fi

# -------------------------------------------------------------
# 3. Wait until MySQL database is reachable
# -------------------------------------------------------------
echo "[Database] Waiting for MySQL database at ${DB_HOST:-mysql}:${DB_PORT:-3306}..."
python - << 'EOF'
import os
import sys
import time
import MySQLdb

host = os.getenv("DB_HOST", "mysql")
port = int(os.getenv("DB_PORT", "3306"))
user = os.getenv("DB_USER", "lawlense")
password = os.getenv("DB_PASSWORD", "lawlense_password")
database = os.getenv("DB_NAME", "lawlense")

max_retries = 60
for attempt in range(1, max_retries + 1):
    try:
        conn = MySQLdb.connect(
            host=host,
            port=port,
            user=user,
            passwd=password,
            db=database,
            connect_timeout=3,
        )
        conn.close()
        print(f"[Database] Successfully connected to MySQL on attempt {attempt}.")
        sys.exit(0)
    except Exception as exc:
        if attempt % 5 == 0 or attempt == 1:
            print(f"[Database] Waiting for MySQL to become ready (attempt {attempt}/{max_retries})...")
        time.sleep(2)

print("[Database ERROR] Timed out waiting for MySQL database.", file=sys.stderr)
sys.exit(1)
EOF

# -------------------------------------------------------------
# 4. Run database migrations
# -------------------------------------------------------------
echo "[Database] Running database migrations..."
python backend/manage.py migrate --noinput

# -------------------------------------------------------------
# 5. Seed BNS sections into MySQL
# -------------------------------------------------------------
echo "[Database] Seeding BNS sections into MySQL..."
python backend/manage.py seed_bns

# -------------------------------------------------------------
# 6. Start the requested command or default to runserver
# -------------------------------------------------------------
echo "============================================================"
echo "LawLense Initialization Complete. Starting Application."
echo "============================================================"

if [ $# -eq 0 ]; then
    exec python backend/manage.py runserver 0.0.0.0:8000
else
    exec "$@"
fi
