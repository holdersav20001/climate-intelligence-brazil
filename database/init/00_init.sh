#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE EXTENSION IF NOT EXISTS "pgcrypto";
    CREATE EXTENSION IF NOT EXISTS "vector";
    CREATE SCHEMA IF NOT EXISTS climate;
    GRANT ALL ON SCHEMA climate TO $POSTGRES_USER;
EOSQL

echo "climate schema and extensions created"
