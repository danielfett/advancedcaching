#!/bin/bash
PKGROOT='agtl-meego/'
VERSION=$1
BUILD=$2
if [ "$VERSION" == "" ] ; then 
	echo "gimme version, plz"
#	exit
fi
if [ "$BUILD" == "" ] ; then
	echo "gimme build, plz"
#	exit
fi
cp $PKGROOT/setup.py $PKGROOT/setup.py.tmp
rm $PKGROOT/*.py
cp files/advancedcaching/utils.py files/advancedcaching/astral.py files/advancedcaching/connection.py files/advancedcaching/gpsreader.py files/advancedcaching/cachedownloader.py files/advancedcaching/coordfinder.py files/advancedcaching/geo.py files/advancedcaching/gui.py files/advancedcaching/cli.py files/advancedcaching/core.py files/advancedcaching/geocaching.py files/advancedcaching/provider.py files/advancedcaching/colorer.py files/advancedcaching/downloader.py files/advancedcaching/geonames.py files/advancedcaching/qmlgui.py $PKGROOT/
cp $PKGROOT/setup.py.tmp $PKGROOT/setup.py
cp files/advancedcaching-64.png $PKGROOT/agtl-meego.png
rsync -av --delete files/advancedcaching/data $PKGROOT/
rsync -av --delete files/advancedcaching/qml $PKGROOT/
rsync -av --delete files/advancedcaching/actors $PKGROOT/
cd $PKGROOT
../PySideAssistant/psa build-deb
