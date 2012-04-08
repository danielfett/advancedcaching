#!/bin/bash
DIST=maemo-psa
source settings
BUILD=0
PKGROOT=maemo-psa
PYSIDE_ASSISTANT=`pwd`/../PySideAssistant/psa
PYSIDE_ROOT=`pwd`/../PySideAssistant/
PYSIDE_PROJECT_NAME=agtl-maemo
echo " Build number is $BUILD"
echo " Copying packaging files from $PKGROOT"
echo " Expecting PySideAssistant executable at $PYSIDE_ASSISTANT"
# Check if source path exists
if [ ! -e $SOURCE ]; then
	echo "Source path does not exist; Exiting!"
	exit
fi
# Check if PySideAssistant is available
if [ ! -e $PYSIDE_ASSISTANT ]; then
        echo "PySideAssistant is missing; Exiting!"
        echo "To get PSA, run:"
        echo " cd ..; git clone git://github.com/webhamster/PySideAssistant.git"
        exit
fi
# Create destination dir if necessary
mkdir -p $PKG
mkdir -p $PKGTMP
# Copy template files for PySideAssistant
cp $PKGROOT/* $PKGTMP/
sed -e "s/___VERSION___/$VERSION/" $PKGROOT/setup.py > $PKGTMP/setup.py
# Copy python sources 
cp $SOURCE/utils.py $SOURCE/astral.py $SOURCE/connection.py $SOURCE/gpsreader.py $SOURCE/cachedownloader.py $SOURCE/coordfinder.py $SOURCE/geo.py $SOURCE/gui.py $SOURCE/cli.py $SOURCE/core.py $SOURCE/geocaching.py $SOURCE/provider.py $SOURCE/colorer.py $SOURCE/downloader.py $SOURCE/geonames.py $SOURCE/hildongui.py $SOURCE/simplegui.py $SOURCE/hildon_plugins.py $SOURCE/gtkmap.py $SOURCE/abstractmap.py $SOURCE/openstreetmap.py $SOURCE/portrait.py $SOURCE/threadpool.py $PKGTMP/
# Copy icon
cp $RES/advancedcaching-64.png $PKGTMP/agtl-maemo.png
# Copy additional resources
cp -r $SOURCE/data $PKGTMP/
cp -r $SOURCE/actors $PKGTMP/
cd $PKGTMP
PSA_ROOT=$PYSIDE_ROOT $PYSIDE_ASSISTANT --project $PYSIDE_PROJECT_NAME build-deb
cd -
cp $PKGTMP/deb_dist/${PYSIDE_PROJECT_NAME}_${VERSION}-1_all.deb $PKG
