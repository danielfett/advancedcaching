#!/bin/bash
DIST=meego-debuild
source settings
BUILD=0
PKGROOT=meego-debuild
echo " Build number is $BUILD"
echo " Copying packaging files from $PKGROOT"
# Check if source path exists
if [ ! -e $SOURCE ]; then
	echo "Source path does not exist; Exiting!"
	exit
fi
# Check if dest exists
if [ -e $PKG ]; then
	echo "Package path exists; Exiting!"
	echo "To delete, run rm -r $PKG"
	exit
fi
# Create destination dir if necessary
#mkdir -p $PKG
mkdir -p $PKGTMP

cp -a $PKGROOT/* $PKGTMP/
mkdir -p $PKGTMP/src/opt/advancedcaching/
cp changelog $PKGTMP/debian/
# Copy python sources 
rsync -av --delete --exclude='*.pyc' \
    $SOURCE/utils.py \
    $SOURCE/astral.py \
    $SOURCE/connection.py \
    $SOURCE/gpsreader.py \
    $SOURCE/cachedownloader.py \
    $SOURCE/coordfinder.py \
    $SOURCE/geo.py \
    $SOURCE/gui.py \
    $SOURCE/cli.py \
    $SOURCE/core.py \
    $SOURCE/geocaching.py \
    $SOURCE/provider.py \
    $SOURCE/colorer.py \
    $SOURCE/downloader.py \
    $SOURCE/geonames.py \
    $SOURCE/qmlgui.py \
    $PKGTMP/src/opt/advancedcaching/
    
find $PKGTMP/src/opt/advancedcaching/ -iname '*.pyc' | xargs rm -f
# Copy additional resources
cp -r $SOURCE/data $PKGTMP/src/opt/advancedcaching/
cp -r $SOURCE/actors $PKGTMP/src/opt/advancedcaching/
cp -r $SOURCE/qml $PKGTMP/src/opt/advancedcaching/
mkdir -p $PKGTMP/src/usr/share/icons/hicolor/80x80/apps/
cp $RES/advancedcaching-80.png $PKGTMP/src/usr/share/icons/hicolor/80x80/apps/advancedcaching.png
cd $PKGTMP/
debuild --no-lintian -aarmel 
cd -
echo "Now run PATH=\$PATH:`pwd`/aegis-builder/ perl aegis-builder/aegis-deb-util --verbose --add-manifest --manifest=meego-debuild/_aegis --add-digsigsums='/opt/advancedcaching/launch' <debfile>"
