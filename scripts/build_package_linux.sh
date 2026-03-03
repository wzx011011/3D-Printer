#!/bin/bash
cp_source="/workspaces/C3DSlicer/"
cd $cp_source
git config --global --add safe.directory /workspaces/C3DSlicer
echo $1 $2 $3 $4 $6
JOB_NAME=$6
TAG_NAME=$2
TAGNUMB=$(git rev-list HEAD --count)
VERSION=${TAG_NAME}.${TAGNUMB}
APP_NAME=$3
RTYPE=$4
SLICER_HEADER=$5
#/usr/bin/python3 ./scripts/generate_creality_presets.py -b $4 -n "3.0.0" || exit -1
#echo scripts/BuildLinux_Package.sh -sir $VERSION $APP_NAME $RTYPE $SLICER_HEADER
rm -rf /workspaces/C3DSlicer/deps/build/
mkdir -p /workspaces/C3DSlicer/deps/build/
ln -s /workspaces/destdir /workspaces/C3DSlicer/deps/build/
scripts/BuildLinux_Package.sh -sir $VERSION $APP_NAME $RTYPE $SLICER_HEADER || exit -1
echo "Upload..."
VERSIONID=`grep VERSION_ID /etc/os-release | cut -d'"' -f2`
echo "V"
if [ "$VERSIONID" == "24.04" ]; then
    R_APP_NAME=$APP_NAME'_Ubuntu2404'
    echo "is ubuntu"$R_APP_NAME
else
	R_APP_NAME=$APP_NAME
fi
echo $R_APP_NAME
scp -P 9122 ./build/${APP_NAME}-V${VERSION}-x86_64-${RTYPE}.AppImage cxsw@172.20.180.14:/vagrant_data/www/shared/build/$JOB_NAME/${R_APP_NAME}-V${VERSION}-x86_64-${RTYPE}.AppImage
chmod 777 build
chmod 777 build/${APP_NAME}-V${VERSION}-x86_64-${RTYPE}.AppImage
exit 0
