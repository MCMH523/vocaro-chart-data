#!/bin/sh
# usage: wait_file.sh REPO_DIR FILE SINCE_EPOCH_SECONDS [MAX_SECONDS]
# Pulls until FILE (path inside the repository) was committed after SINCE (default wait up to 600 s).
# Exit 0 when it arrived, 1 on timeout.
dir=$1; file=$2; since=$3; max=${4:-600}; waited=0
while [ "$waited" -lt "$max" ]; do
  git -C "$dir" pull -q --rebase >/dev/null 2>&1
  ts=$(git -C "$dir" log -1 --format=%ct -- "$file")
  if [ -n "$ts" ] && [ "$ts" -ge "$since" ]; then echo "$file committed at $ts"; exit 0; fi
  sleep 10; waited=$((waited + 10))
done
echo "no new $file after ${max}s"; exit 1
