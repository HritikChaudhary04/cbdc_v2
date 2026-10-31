#!/usr/bin/env bash
# Resource sampler (step 7b, D): CPU and memory of every container, about every 2 s, until killed.
# CPU % is per core (100% = one full core). Runs on the client cores (07_benchmark.sh starts it under taskset).
out="$1"; echo "utc,container,cpu_percent,mem_usage" > "$out"
trap 'exit 0' TERM INT
while true; do
  ts=$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)
  docker stats --no-stream --format '{{.Name}},{{.CPUPerc}},{{.MemUsage}}' 2>/dev/null | sed "s/^/$ts,/" >> "$out"
  sleep 1
done
