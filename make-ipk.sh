#!/bin/sh
IPKG='ipkg-utils-1.7/ipkg-build'
PKGROOT='freerunner'
VERSION="Version: "`grep -oP "(?<=version=').*(?=')" files/setup.py`

cp --preserve=all files/agtl     $PKGROOT/usr/bin/
cp files/advancedcaching.desktop $PKGROOT/usr/share/applications/
cp files/advancedcaching.png     $PKGROOT/usr/share/pixmaps/
cp -R files/advancedcaching/*	 $PKGROOT/usr/lib/site-python/advancedcaching/
rm $PKGROOT/usr/lib/site-python/advancedcaching/*.pyc
sed -i -e "s/Version: .*/$VERSION/" $PKGROOT/CONTROL/control

$IPKG -o root -g root freerunner
