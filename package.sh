#!/bin/bash
VERSION=0.1
NAME=anr
TARBALL=${NAME}-$VERSION.tar.gz
tar czvf $TARBALL \
    anr.py \
    fetchtelemetry.py \
    mapreduce-dims.py \
    mapreduce-sessions.py \
    mapreduce-summary.py \
    mapreduce_common.py \
    run.sh

if [ ! -z "$(which aws)" ]; then
    aws s3 cp $TARBALL s3://telemetry-analysis-code/$NAME/$TARBALL
fi
