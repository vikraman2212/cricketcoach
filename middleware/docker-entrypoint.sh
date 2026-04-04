#!/usr/bin/env bash
set -e

# ── Initialise PostgreSQL data directory if needed ─────────────────────────
if [ ! -s "$PGDATA/PG_VERSION" ]; then
    echo "Initialising PostgreSQL data directory..."
    chown -R postgres:postgres "$PGDATA" 2>/dev/null || true
    su -s /bin/sh postgres -c "initdb -D $PGDATA --auth-local trust --auth-host md5" > /dev/null
fi

# ── Start the PostgreSQL server ────────────────────────────────────────────
echo "Starting PostgreSQL..."
su -s /bin/sh postgres -c "pg_ctl start -D $PGDATA -o '-c listen_addresses=localhost' -w -t 30" > /dev/null

# ── Create the application database and user ──────────────────────────────
echo "Setting up database..."
su -s /bin/sh postgres -c "psql -tc \"SELECT 1 FROM pg_roles WHERE rolname='${POSTGRES_USER}'\" | grep -q 1 || \
    psql -c \"CREATE USER ${POSTGRES_USER} WITH PASSWORD '${POSTGRES_PASSWORD}';\""
su -s /bin/sh postgres -c "psql -tc \"SELECT 1 FROM pg_database WHERE datname='${POSTGRES_DB}'\" | grep -q 1 || \
    psql -c \"CREATE DATABASE ${POSTGRES_DB} OWNER ${POSTGRES_USER};\""

# ── Launch the Spring Boot application ────────────────────────────────────
echo "Starting Spring Boot application..."
exec java -jar /app/app.jar
