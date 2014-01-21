#!/bin/bash
START=$1
END=$2
if [ -z "$START" -o -z "$END" ]; then
  # Arguments missing. Default to the previous week
  START=$(date -d 'last saturday - 6 days' +%Y%m%d)
  END=$(date -d 'last saturday' +%Y%m%d)
fi

sudo chown -R ubuntu:ubuntu /mnt

FIRST_OUTPUT_DIR=/mnt/anr-$START-$END
if [ ! -d "$FIRST_OUTPUT_DIR" ]; then
    mkdir -p "$FIRST_OUTPUT_DIR"
fi

echo "Running ANR analyzer for $START to $END"

BASE=$(pwd)
cd ~/telemetry-server
python $BASE/fetchtelemetry.py $START $END
echo "Job exited with code: $?"
cd -
echo "Moving $FIRST_OUTPUT_DIR to final output dir"
mv $FIRST_OUTPUT_DIR output/
echo "Done!"
