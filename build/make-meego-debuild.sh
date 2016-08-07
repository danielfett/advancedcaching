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

cp -r $PKGROOT/DEBIAN $PKGTMP
cp changelog $PKGTMP/DEBIAN
sed -i "s/Homepage:/Version: "$VERSION"\nHomepage:/" $PKGTMP/DEBIAN/control

mkdir -p $PKGTMP/opt/advancedcaching/
cp $PKGROOT/launch.sh $PKGTMP/opt/advancedcaching/

mkdir -p $PKGTMP/usr/share/applications/
cp $PKGROOT/advancedcaching.desktop   $PKGTMP/usr/share/applications/

# Copy python sources 
cp \
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
    $PKGTMP/opt/advancedcaching/
    
# Copy additional resources
cp -r $SOURCE/data $PKGTMP/opt/advancedcaching/
cp -r $SOURCE/actors $PKGTMP/opt/advancedcaching/
cp -r $SOURCE/qml $PKGTMP/opt/advancedcaching/
cp -r $RES/splash.png $PKGTMP/opt/advancedcaching/

mkdir -p $PKGTMP/usr/share/icons/hicolor/80x80/apps/
cp -r $RES/advancedcaching-80.png $PKGTMP/usr/share/icons/hicolor/80x80/apps/advancedcaching.png

cd $PKGTMP/

echo
echo Calculate md5sums
for line in `find . -type f -follow -print | grep -v "./DEBIAN" | cut -c 3-`
do
 if [ -f "$line" ]; then
  md5sum "$line" >> DEBIAN/md5sums
 fi
done
cd -
cd $PKGTMP/..

echo
echo Generate deb
#mv $PKGTMP $PKG/advancedcaching-$VERSION
fakeroot dpkg-deb -b -Zgzip temp advancedcaching-$VERSION.deb
cd -

echo
echo "Running aegis-build:"
PATH=$PATH:`pwd`/aegis-builder/ perl aegis-builder/aegis-deb-util --verbose --add-manifest --manifest=meego-debuild/_aegis --add-digsigsums='/opt/advancedcaching/launch.sh' --add-digsigsums='/opt/advancedcaching/core.py' `ls $PKG/*.deb`

