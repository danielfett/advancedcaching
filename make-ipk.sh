#!/bin/sh
IPKG='ipkg-utils-1.7/ipkg-build'
PKGROOT='freerunner'
VERSION="Version: "`grep -oP "(?<=version=').*(?=')" files/setup.py`

cp files/advancedcaching.desktop $PKGROOT/usr/share/applications/
cp files/advancedcaching.png     $PKGROOT/usr/share/pixmaps/
cp -R files/advancedcaching/*	 $PKGROOT/usr/lib/site-python/advancedcaching/
rm $PKGROOT/usr/lib/site-python/advancedcaching/*.pyc
rm $PKGROOT/usr/lib/site-python/advancedcaching/*.pyo
sed -i -e "s/Version: .*/$VERSION/" $PKGROOT/CONTROL/control

$IPKG -o root -g root freerunner
