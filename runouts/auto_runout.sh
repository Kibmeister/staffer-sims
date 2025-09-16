#!/bin/bash
# auto_runout.sh: Find next available runN.out in runouts/, rotate if >100 files
DIR="$(dirname "$0")"
OUTDIR="$DIR"
MAX=100

mkdir -p "$OUTDIR"

# Count and rotate if needed
count=$(ls "$OUTDIR"/run*.out 2>/dev/null | wc -l)
if [ "$count" -ge "$MAX" ]; then
  # Delete oldest
  oldest=$(ls -1t "$OUTDIR"/run*.out | tail -1)
  rm -f "$oldest"
fi

# Find next available runN.out
n=1
while [ -e "$OUTDIR/run$n.out" ]; do
  n=$((n+1))
done

# Print the next filename
echo "$OUTDIR/run$n.out"
