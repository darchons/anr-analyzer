#!/bin/bash
VERSION=0.2
NAME=anr
TARBALL=${NAME}-$VERSION.tar.gz
tar czvf $TARBALL \
    run.sh
S3PATH=s3://telemetry-analysis-code/$NAME/$TARBALL

echo "Packaged $NAME code as $TARBALL"
if [ ! -z "$(which aws)" ]; then
    aws s3 cp $TARBALL $S3PATH
    echo "Code successfully uploaded to S3"
else
    echo "AWS CLI not found - you should manually upload to $S3PATH"
fi
