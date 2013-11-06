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
mkdir -p $PKGTMP/src/opt/agtl-maemo/
cp changelog $PKGTMP/debian/
# Copy python sources 
rsync -av --delete --exclude='*.pyc' $SOURCE/utils.py $SOURCE/astral.py $SOURCE/connection.py $SOURCE/gpsreader.py $SOURCE/cachedownloader.py $SOURCE/coordfinder.py $SOURCE/geo.py $SOURCE/gui.py $SOURCE/cli.py $SOURCE/core.py $SOURCE/geocaching.py $SOURCE/provider.py $SOURCE/colorer.py $SOURCE/downloader.py $SOURCE/geonames.py $SOURCE/hildongui.py $SOURCE/simplegui.py $SOURCE/hildon_plugins.py $SOURCE/gtkmap.py $SOURCE/abstractmap.py $SOURCE/openstreetmap.py $SOURCE/portrait.py $SOURCE/threadpool.py $PKGTMP/src/opt/agtl-maemo/
find $PKGTMP/src/opt/agtl-maemo/ -iname '*.pyc' | xargs rm 
# Copy additional resources
cp -r $SOURCE/data $PKGTMP/src/opt/agtl-maemo/
cp -r $SOURCE/actors $PKGTMP/src/opt/agtl-maemo/
mkdir -p $PKGTMP/src/usr/share/icons/hicolor/64x64/apps/
cp $RES/advancedcaching-64.png $PKGTMP/src/usr/share/icons/hicolor/64x64/apps/agtl-maemo.png
cd $PKGTMP/

debuild -aarmel 
