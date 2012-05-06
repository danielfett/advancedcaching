#!/bin/bash
DIST=maemo-debuild
source settings
BUILD=0
PKGROOT=maemo-debuild
echo " Build number is $BUILD"
echo " Copying packaging files from $PKGROOT"
# Check if source path exists
if [ ! -e $SOURCE ]; then
	echo "Source path does not exist; Exiting!"
	exit
fi
# Create destination dir if necessary
mkdir -p $PKG
mkdir -p $PKGTMP

cp -a $PKGROOT/* $PKGTMP/
mkdir -p $PKGTMP/src/opt/agtl-maemo/
#sed -e "s/___VERSION___/$VERSION/" $PKGROOT/setup.py > $PKGTMP/setup.py
# Copy python sources 
cp $SOURCE/utils.py $SOURCE/astral.py $SOURCE/connection.py $SOURCE/gpsreader.py $SOURCE/cachedownloader.py $SOURCE/coordfinder.py $SOURCE/geo.py $SOURCE/gui.py $SOURCE/cli.py $SOURCE/core.py $SOURCE/geocaching.py $SOURCE/provider.py $SOURCE/colorer.py $SOURCE/downloader.py $SOURCE/geonames.py $SOURCE/hildongui.py $SOURCE/simplegui.py $SOURCE/hildon_plugins.py $SOURCE/gtkmap.py $SOURCE/abstractmap.py $SOURCE/openstreetmap.py $SOURCE/portrait.py $SOURCE/threadpool.py $PKGTMP/src/opt/agtl-maemo/
# Copy additional resources
cp -r $SOURCE/data $PKGTMP/src/opt/agtl-maemo/
cp -r $SOURCE/actors $PKGTMP/src/opt/agtl-maemo/
cd $PKGTMP/
#PSA_ROOT=$PYSIDE_ROOT $PYSIDE_ASSISTANT --project $PYSIDE_PROJECT_NAME build-deb
debuild
#cd -
#cp $PKGTMP/deb_dist/${PYSIDE_PROJECT_NAME}_${VERSION}-1_all.deb $PKG
