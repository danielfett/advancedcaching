import QtQuick 1.1
import QtMobility.location 1.2

Rectangle {
    id: pinchmap;
    property double centerLatitude: 49;
    property double centerLongitude: 6;
    property int zoomLevel: 10;
    property int tileSize: 256;
    property int cornerTileX: 32;
    property int cornerTileY: 21;
    property int numTilesX: Math.ceil(width/tileSize) + 4;
    property int numTilesY: Math.ceil(height/tileSize) + 4;

    Component.onCompleted: {
        setZoomLevel(zoomLevel);
        setCenterLatLon(centerLatitude, centerLongitude)
    }

    onCenterLongitudeChanged: {
        setCenterLatLon(centerLatitude, centerLongitude);
    }

    function setZoomLevel(z) {
        setZoomLevelPoint(pinchmap.width/2, pinchmap.height/2);
    }

    function setZoomLevelPoint(z, x, y) {
        if (z == zoomLevel) {
            return;
        }
        if (z < 1 || z > 17) {
            return;
        }
        var p = getCoordFromScreenpoint(x, y);
        zoomLevel = z;
        setCoord(p, x, y);
    }

    function pan(dx, dy) {
        map.offsetX -= dx;
        map.offsetY -= dy;
        var changed = false;
        var threshold = parent.tileSize;
        if (map.offsetX < -threshold) {
            map.offsetX += threshold;
            cornerTileX += 1;
            changed = true;
        } else if (map.offsetX > threshold) {
            map.offsetX -= threshold;
            cornerTileX -= 1;
            changed = true;
        }

        if (map.offsetY < -threshold) {
            map.offsetY += threshold;
            cornerTileY += 1;
            changed = true;
        } else if (map.offsetY > threshold) {
            map.offsetY -= threshold;
            cornerTileY -= 1;
            changed = true;
        }
        if (changed) {
            populate();
        }
    }
    function populate() {
        var i = 0;
        var maxTileNo = Math.pow(2, zoomLevel) - 1;
        for (i = 0; i < (numTilesX * numTilesY); i++) {
            var tx = cornerTileX + (i % numTilesX);
            var ty = cornerTileY + Math.floor(i / numTilesX);
            if (tx < 0) {
                tx += maxTileNo + 1;
            } else if (tx > maxTileNo - 1) {
                tx -= maxTileNo + 1;
            }
            if (ty < 0 || ty > maxTileNo -1) {
                map.children[i].source = "../data/noimage.png";
            } else {
                map.children[i].source = "http://a.tile2.opencyclemap.org/transport/" + zoomLevel + "/" + tx + "/" + ty + ".png";
            }
        }
    }
    function deg2rad(deg) {
        return deg * (Math.PI /180.0);
    }

    function deg2num(lat, lon) {
        var rad = deg2rad(lat);
        var n = Math.pow(2, zoomLevel);
        var xtile = (lon + 180.0) / 360.0 * n;
        var ytile = (1.0 - Math.log(Math.tan(rad) + (1.0 / Math.cos(rad))) / Math.PI) / 2.0 * n;
        return [xtile, ytile];
    }
    function setLatLon(lat, lon, x, y) {
        var tile = deg2num(lat, lon);
        var cornerTileFloatX = tile[0] + (map.rootX - x) / tileSize // - numTilesX/2.0;
        var cornerTileFloatY = tile[1] + (map.rootY - y) / tileSize // - numTilesY/2.0;
        cornerTileX = Math.floor(cornerTileFloatX);
        cornerTileY = Math.floor(cornerTileFloatY);
        map.offsetX = -(cornerTileFloatX - Math.floor(cornerTileFloatX)) * tileSize;
        map.offsetY = -(cornerTileFloatY - Math.floor(cornerTileFloatY)) * tileSize;

        populate();
    }
    function setCoord(c, x, y) {
        setLatLon(c[0], c[1], x, y);
    }
    function setCenterLatLon(lat, lon) {
        setLatLon(lat, lon, pinchmap.width/2, pinchmap.height/2);
    }
    function setCenterCoord(c) {
        setCenterLatLon(c[0], c[1]);
    }
    function getCoordFromScreenpoint(x, y) {
        var realX = - map.rootX - map.offsetX + x;
        var realY = - map.rootY - map.offsetY + y;
        var realTileX = cornerTileX + realX / tileSize;
        var realTileY = cornerTileY + realY / tileSize;
        return num2deg(realTileX, realTileY);
    }
    function getCenter() {
        return getCoordFromScreenpoint(pinchmap.width/2, pinchmap.height/2);
    }
    function sinh(aValue)
    {
        var myTerm1 = Math.pow(Math.E, aValue);
        var myTerm2 = Math.pow(Math.E, -aValue);

        return (myTerm1-myTerm2)/2;
    }
    function num2deg(xtile, ytile) {
        var n = Math.pow(2, zoomLevel);
        var lon_deg = xtile / n * 360.0 - 180;
        var lat_rad = Math.atan(sinh(Math.PI * (1 - 2 * ytile / n)));
        var lat_deg = lat_rad * 180.0 / Math.PI;
        return [lat_deg, lon_deg];
    }

    Grid {
        id: map;
        columns: numTilesX;
        width: numTilesX * tileSize;
        height: numTilesY * tileSize;
        property int rootX: -(width - parent.width)/2;
        property int rootY: -(height - parent.height)/2;
        property int offsetX: 0;
        property int offsetY: 0;
        x: rootX + offsetX;
        y: rootY + offsetY;

        Repeater {
            model: (pinchmap.numTilesX * pinchmap.numTilesY);
            Rectangle {
                property alias source: img.source;
                Rectangle {
                    id: progressBar;
                    property real p: 0;
                    height: 16;
                    width: parent.width - 32;
                    anchors.centerIn: img;
                    anchors.left: parent.left;
                    anchors.right: parent.right;
                    color: "#c0c0c0";
                    border.width: 1;
                    border.color: "#000000";
                    Rectangle {
                        anchors.left: parent.left;
                        anchors.margins: 2;
                        anchors.top: parent.top;
                        anchors.bottom: parent.bottom;
                        width: (parent.width - 4) * progressBar.p;
                        color: "#000000";
                    }
                }
                Image {
                    id: img;
                    anchors.fill: parent;
                    onProgressChanged: { progressBar.p = progress }
                }
                width: tileSize;
                height: tileSize;
                color: "#c0c0c0";
            }

        }
        /*transform: Scale {
        id: scalemap
        function setScale (sc, screenpointX, screenpointY) {
        scalemap.xScale = sc
        scalemap.yScale = sc

        }
        function getScale() {
        return xScale
        }
        //origin.x: map.width/2
        //origin.y: map.height/2
        }*/
    }
    PinchArea {
        id: pincharea;

        property double __oldZoom;

        anchors.fill: parent;

        function calcZoomDelta(p) {
            /*var newScale = zoom * p.scale
            //pinchmap.zoomLevel += Math.floor(newScale / 2)
            scalemap.setScale(newScale % 2)
            var panX = -(((p.center.x - map.rootX) * newScale)-(p.center.x - map.rootX) )
            //console.log("Scale is now " + newScale +

            pan(panX, -(((p.center.y - map.rootY) * newScale) - (p.center.y - map.rootY)))
            //map.pan(
            //__oldZoom = (newScale % 2)
            //console.log("Now, __oldZoom is " + __oldZoom + " and Map is at " + pinchmap.zoomLevel)
             */
            pinchmap.setZoomLevelPoint(Math.round((Math.log(p.scale)/Math.log(2)) + __oldZoom), p.center.x, p.center.y);

            pan(p.previousCenter.x - p.center.x, p.previousCenter.y - p.center.y);
        }

        onPinchStarted: {
            __oldZoom = pinchmap.zoomLevel;
        }

        onPinchUpdated: {
            calcZoomDelta(pinch);
        }

        onPinchFinished: {
            calcZoomDelta(pinch);
        }
    }
    MouseArea {
        id: mousearea;

        property bool __isPanning: false;
        property int __lastX: -1;
        property int __lastY: -1;

        anchors.fill : parent;

        onPressed: {
            __isPanning = true;
            __lastX = mouse.x;
            __lastY = mouse.y;

        }

        onReleased: {
            __isPanning = false;
        }

        onPositionChanged: {
            if (__isPanning) {
                var dx = mouse.x - __lastX;
                var dy = mouse.y - __lastY;
                pan(-dx, -dy);
                __lastX = mouse.x;
                __lastY = mouse.y;
            }
        }

        onCanceled: {
            __isPanning = false;
        }
    }
}
