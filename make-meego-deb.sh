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
cp files/advancedcaching/*.py $PKGROOT
cp $PKGROOT/setup.py.tmp $PKGROOT/setup.py
cp files/advancedcaching-48.png $PKGROOT/agtl-meego.png
rsync -av files/advancedcaching/data $PKGROOT/
rsync -av files/advancedcaching/qml $PKGROOT/
rsync -av files/advancedcaching/actors $PKGROOT/
cd $PKGROOT
../PySideAssistant/psa build-deb
