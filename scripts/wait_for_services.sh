#!/bin/bash
set -e

TIMEOUT=30
SERVICES=()

usage() {
    echo "Usage: $0 [OPTIONS]"
    echo "Wait for services to be accepting TCP connections."
    echo ""
    echo "Options:"
    echo "  -t, --timeout SECONDS    Timeout in seconds (default: 30)"
    echo "  -s, --service HOST:PORT   Service to check (can be repeated)"
    echo "  -h, --help               Show this help message"
    exit 1
}

while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        -s|--service)
            SERVICES+=("$2")
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

if [ ${#SERVICES[@]} -eq 0 ]; then
    SERVICES=(
        "localhost:5432"
        "localhost:6379"
        "localhost:9000"
    )
fi

wait_for_service() {
    local host="$1"
    local port="$2"
    local name="$3"
    local elapsed=0

    echo "Waiting for $name at $host:$port..."

    while [ $elapsed -lt $TIMEOUT ]; do
        if nc -z "$host" "$port" 2>/dev/null; then
            echo "$name is ready!"
            return 0
        fi
        sleep 1
        elapsed=$((elapsed + 1))
    done

    echo "ERROR: Timeout waiting for $name at $host:$port after ${TIMEOUT}s" >&2
    return 1
}

failed=0

for svc in "${SERVICES[@]}"; do
    IFS=':' read -r host port <<< "$svc"
    name="${svc}"
    wait_for_service "$host" "$port" "$name" || failed=$((failed + 1))
done

if [ $failed -gt 0 ]; then
    echo "ERROR: $failed service(s) failed to respond" >&2
    exit 1
fi

echo "All services are ready!"
