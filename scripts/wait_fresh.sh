#!/bin/sh
# usage: wait_fresh.sh REPO_DIR SINCE_EPOCH_SECONDS [MAX_SECONDS]
# Pulls until data/latest.json was committed by the workflow after SINCE (default wait up to 240 s).
# Exit 0 when a fresh reading arrived, 1 on timeout.
dir=$1; since=$2; max=${3:-240}; waited=0
while [ "$waited" -lt "$max" ]; do
  git -C "$dir" pull -q --rebase >/dev/null 2>&1
  ts=$(git -C "$dir" log -1 --format=%ct -- data/latest.json)
  if [ -n "$ts" ] && [ "$ts" -ge "$since" ]; then echo "fresh reading committed at $ts"; exit 0; fi
  sleep 10; waited=$((waited + 10))
done
echo "no fresh reading after ${max}s"; exit 1
