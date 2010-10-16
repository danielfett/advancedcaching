#!/bin/sh
IPKG='ipkg-utils-1.7/ipkg-build'
PKGROOT='freerunner'
VERSION="Version: "`grep -oP "(?<=version=').*(?=')" files/setup.py`

# create dirs first, maybe they don't exist yet
mkdir -p $PKGROOT/usr/bin/
mkdir -p $PKGROOT/usr/share/applications/
mkdir -p $PKGROOT/usr/share/pixmaps/
mkdir -p $PKGROOT/usr/lib/site-python/advancedcaching/

# copy files for package to their desired place
cp --preserve=all files/agtl     $PKGROOT/usr/bin/
cp files/advancedcaching.desktop $PKGROOT/usr/share/applications/
cp files/advancedcaching.png     $PKGROOT/usr/share/pixmaps/
cp -R files/advancedcaching/*	 $PKGROOT/usr/lib/site-python/advancedcaching/

# remove overhead
rm -rf $PKGROOT/usr/lib/site-python/advancedcaching/*.pyc
rm -rf $PKGROOT/usr/lib/site-python/advancedcaching/*.py~ # remove alls gedit temporary files too

sed -i -e "s/Version: .*/$VERSION/" $PKGROOT/CONTROL/control

$IPKG -o root -g root freerunner
