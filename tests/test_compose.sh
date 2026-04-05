#!/usr/bin/env bash
# tests/test_compose.sh — smoke tests for the Docker Compose dev stack
#
# Validates:
#   1. docker compose config  — YAML is valid and all required services present
#   2. All required service keys exist in the rendered compose config
#
# Does NOT start containers (no Docker daemon required for these checks).
# Run with:   bash tests/test_compose.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PASS=0
FAIL=0

pass() { echo "  ✓ $1"; PASS=$((PASS + 1)); }
fail() { echo "  ✗ $1"; FAIL=$((FAIL + 1)); }

echo "=== Docker Compose smoke tests ==="
echo

# ── 1. Compose config validation ─────────────────────────────────────────────
echo "1. Validating docker-compose.yml syntax..."
if docker compose -f "$REPO_ROOT/docker-compose.yml" config --quiet 2>/dev/null; then
    pass "docker compose config: YAML is valid"
else
    fail "docker compose config: YAML is invalid"
fi

# ── 2. Required services present ─────────────────────────────────────────────
echo "2. Checking required services are defined..."
COMPOSE_CONFIG=$(docker compose -f "$REPO_ROOT/docker-compose.yml" config 2>/dev/null)

for service in minio minio-init speedtracking-api middleware; do
    # Services appear as top-level keys indented by 2 spaces in the rendered YAML
    if echo "$COMPOSE_CONFIG" | grep -qE "^  ${service}:"; then
        pass "service '$service' is present"
    else
        fail "service '$service' is MISSING"
    fi
done

# ── 3. Required ports exposed ─────────────────────────────────────────────────
echo "3. Checking required port mappings..."
REQUIRED_PORTS=("9000:MinIO S3 API" "9001:MinIO console" "8000:speedtracking-api" "8080:middleware")
for entry in "${REQUIRED_PORTS[@]}"; do
    port="${entry%%:*}"
    desc="${entry#*:}"
    if echo "$COMPOSE_CONFIG" | grep -q "published: \"${port}\""; then
        pass "port $port ($desc) is mapped"
    else
        fail "port $port ($desc) is NOT mapped"
    fi
done

# ── 4. Named volume defined ───────────────────────────────────────────────────
echo "4. Checking named volume..."
if echo "$COMPOSE_CONFIG" | grep -qE "^volumes:" && echo "$COMPOSE_CONFIG" | grep -q "minio-data:"; then
    pass "named volume 'minio-data' is defined"
else
    fail "named volume 'minio-data' is MISSING"
fi

# ── 5. Health-checks present ──────────────────────────────────────────────────
echo "5. Checking health-checks..."
for service in minio speedtracking-api middleware; do
    # Extract the block for this service (service names are alphanumeric + hyphens only)
    # and look for a healthcheck key within that block.
    if awk -v svc="$service" \
        'BEGIN{f=0} /^  [a-z]/{f=0} $0 == "  " svc ":"{f=1} f && /healthcheck:/{found=1; exit} END{exit !found}' \
        <<< "$COMPOSE_CONFIG"; then
        pass "service '$service' has a healthcheck"
    else
        fail "service '$service' is missing a healthcheck"
    fi
done

# ── Summary ───────────────────────────────────────────────────────────────────
echo
echo "Results: $PASS passed, $FAIL failed"
if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
