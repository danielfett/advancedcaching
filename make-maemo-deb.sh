#!/bin/sh
#IPKG='../ipkg-utils-1.7/ipkg-build'
PKGROOT='maemo/advancedcaching/src/'
VERSION=$1
if [ "$VERSION" == "" ] ; then 
	echo "gimme version, plz"
	exit
fi

cp files/advancedcaching-48.png     $PKGROOT/usr/share/icons/hicolor/48x48/hildon/advancedcaching.png
cp -R files/advancedcaching/*	 $PKGROOT/opt/advancedcaching/
rm $PKGROOT/opt/advancedcaching/*.pyc
sed -i -e "s/version = \".*\"/version = \"$VERSION\"/" $PKGROOT/../build_myapp.py
cd $PKGROOT
cd ..
python2.5 build_myapp.py

