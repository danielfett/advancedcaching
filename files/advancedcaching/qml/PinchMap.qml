import QtQuick 1.1
import com.nokia.meego 1.0
import "functions.js" as F

Rectangle {
    id: pinchmap;
    //property double centerLatitude: 0;
    //property double centerLongitude: 0;
    property int zoomLevel: 10;
    property int oldZoomLevel: 99
    property int maxZoomLevel: 17;
    property int minZoomLevel: 2;
    property int minZoomLevelShowGeocaches: 9;
    property int tileSize: 256;
    property int cornerTileX: 32;
    property int cornerTileY: 21;
    property int numTilesX: Math.ceil(width/tileSize) + 2;
    property int numTilesY: Math.ceil(height/tileSize) + 2;
    property int maxTileNo: Math.pow(2, zoomLevel) - 1;
    property bool showTargetIndicator: false
    property double showTargetAtLat: 0;
    property double showTargetAtLon: 0;

    property bool showCurrentPosition: false;
    property bool currentPositionValid: false;
    property double currentPositionLat: 0;
    property double currentPositionLon: 0;
    property double currentPositionAzimuth: 0;
    property double currentPositionError: 0;

    property bool rotationEnabled: false

    property double latitude: 0
    property double longitude: 0
    property variant scaleBarLength: getScaleBarLength(latitude);
    
    property alias angle: rot.angle

    property string url: ""//settings.currentMapType.url

    property int earthRadius: 6371000

    property bool tooManyPoints: true

    property alias model: geocacheDisplay.model

    transform: Rotation {
        angle: 0
        origin.x: pinchmap.width/2
        origin.y: pinchmap.height/2
        id: rot
    }

    onMaxZoomLevelChanged: {
        if (pinchmap.maxZoomLevel < pinchmap.zoomLevel) {
            setZoomLevel(maxZoomLevel);
        }
    }

    onWidthChanged: {
        pinchmap.setCenterLatLon(pinchmap.latitude, pinchmap.longitude);
    }

    onHeightChanged: {
        pinchmap.setCenterLatLon(pinchmap.latitude, pinchmap.longitude);
    }


    function setZoomLevel(z) {
        setZoomLevelPoint(z, pinchmap.width/2, pinchmap.height/2);
    }

    function zoomIn() {
        setZoomLevel(pinchmap.zoomLevel + 1)
    }

    function zoomOut() {
        setZoomLevel(pinchmap.zoomLevel - 1)
    }

    function setZoomLevelPoint(z, x, y) {
        if (z == zoomLevel) {
            return;
        }
        if (z < pinchmap.minZoomLevel || z > pinchmap.maxZoomLevel) {
            return;
        }
        var p = getCoordFromScreenpoint(x, y);
        zoomLevel = z;
        setCoord(p, x, y);
    }

    function pan(dx, dy) {
        map.offsetX -= dx;
        map.offsetY -= dy;
    }

    function panEnd() {
        var changed = false;
        var threshold = pinchmap.tileSize;

        while (map.offsetX < -threshold) {
            map.offsetX += threshold;
            cornerTileX += 1;
            changed = true;
        }
        while (map.offsetX > threshold) {
            map.offsetX -= threshold;
            cornerTileX -= 1;
            changed = true;
        }

        while (map.offsetY < -threshold) {
            map.offsetY += threshold;
            cornerTileY += 1;
            changed = true;
        }
        while (map.offsetY > threshold) {
            map.offsetY -= threshold;
            cornerTileY -= 1;
            changed = true;
        }
        updateCenter();
    }

    function updateCenter() {
        var l = getCenter()
        longitude = l[1]
        latitude = l[0]
        updateGeocaches();
    }

    function requestUpdate() {
        var start = getCoordFromScreenpoint(0,0)
        var end = getCoordFromScreenpoint(pinchmap.width,pinchmap.height)
        controller.updateGeocaches(start[0], start[1], end[0], end[1])
        console.debug("Update requested.")
    }

    function requestUpdateDetails() {
        var start = getCoordFromScreenpoint(0,0)
        var end = getCoordFromScreenpoint(pinchmap.width,pinchmap.height)
        controller.downloadGeocaches(start[0], start[1], end[0], end[1])
        console.debug("Download requested.")
    }

    function getScaleBarLength(lat) {
        var destlength = width/5;
        var mpp = getMetersPerPixel(lat);
        var guess = mpp * destlength;
        var base = 10 * -Math.floor(Math.log(guess)/Math.log(10) + 0.00001)
        var length_meters = Math.round(guess/base)*base
        var length_pixels = length_meters / mpp
        return [length_pixels, length_meters]
    }

    function getMetersPerPixel(lat) {
        return Math.cos(lat * Math.PI / 180.0) * 2.0 * Math.PI * earthRadius / (256 * (maxTileNo + 1))
    }

    function deg2rad(deg) {
        return deg * (Math.PI /180.0);
    }

    function deg2num(lat, lon) {
        var rad = deg2rad(lat % 90);
        var n = maxTileNo + 1;
        var xtile = ((lon % 180.0) + 180.0) / 360.0 * n;
        var ytile = (1.0 - Math.log(Math.tan(rad) + (1.0 / Math.cos(rad))) / Math.PI) / 2.0 * n;
        return [xtile, ytile];
    }
    function setLatLon(lat, lon, x, y) {
        var oldCornerTileX = cornerTileX
        var oldCornerTileY = cornerTileY
        var tile = deg2num(lat, lon);
        var cornerTileFloatX = tile[0] + (map.rootX - x) / tileSize // - numTilesX/2.0;
        var cornerTileFloatY = tile[1] + (map.rootY - y) / tileSize // - numTilesY/2.0;
        cornerTileX = Math.floor(cornerTileFloatX);
        cornerTileY = Math.floor(cornerTileFloatY);
        map.offsetX = -(cornerTileFloatX - Math.floor(cornerTileFloatX)) * tileSize;
        map.offsetY = -(cornerTileFloatY - Math.floor(cornerTileFloatY)) * tileSize;
        updateCenter();
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
    function getScreenpointFromCoord(lat, lon) {
        var tile = deg2num(lat, lon)
        var realX = (tile[0] - cornerTileX) * tileSize
        var realY = (tile[1] - cornerTileY) * tileSize
        var x = realX + map.rootX + map.offsetX
        var y = realY + map.rootY + map.offsetY
        return [x, y]
    }
    function getMappointFromCoord(lat, lon) {
        var tile = deg2num(lat, lon)
        var realX = (tile[0] - cornerTileX) * tileSize
        var realY = (tile[1] - cornerTileY) * tileSize
        return [realX, realY]
        
    }


    function getCenter() {
        return getCoordFromScreenpoint(pinchmap.width/2, pinchmap.height/2);
    }
    function sinh(aValue)
    {
        return (Math.pow(Math.E, aValue)-Math.pow(Math.E, -aValue))/2;
    }
    function num2deg(xtile, ytile) {
        var n = Math.pow(2, zoomLevel);
        var lon_deg = xtile / n * 360.0 - 180;
        var lat_rad = Math.atan(sinh(Math.PI * (1 - 2 * ytile / n)));
        var lat_deg = lat_rad * 180.0 / Math.PI;
        return [lat_deg % 90.0, lon_deg % 180.0];
    }

    function tileUrl(tx, ty) {
        if (ty < 0 || ty > maxTileNo) {
            return "../data/noimage.png"
        } else {
            var x = F.getMapTile(url, tx, ty, zoomLevel);
            return x
        }
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
            id: tiles


            model: (pinchmap.numTilesX * pinchmap.numTilesY);
            Rectangle {
                id: tile
                property alias source: img.source;
                property int tileX: cornerTileX + (index % numTilesX)
                property int tileY: cornerTileY + Math.floor(index / numTilesX)
                Rectangle {
                    id: progressBar;
                    property real p: 0;
                    height: 16;
                    width: parent.width - 32;
                    anchors.centerIn: img;
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
                Label {
                    anchors.left: parent.left
                    anchors.leftMargin: 16
                    y: parent.height/2 - 32
                    text: (img.status == Image.Ready ? "Ready" :
                           img.status == Image.Null ? "Not Set" :
                           img.status == Image.Error ? "Error" :
                           "Loading...")
                }

                Image {
                    id: img;
                    anchors.fill: parent;
                    onProgressChanged: { progressBar.p = progress }
                    source: tileUrl(tileX, tileY);
                }


                width: tileSize;
                height: tileSize;
                color: "#c0c0c0";
            }

        }

        Item {
            id: geocacheDisplayContainer
            Repeater {
                id: geocacheDisplay
                delegate: Geocache {
                    cache: model.geocache
                    targetPoint: getMappointFromCoord(model.geocache.lat, model.geocache.lon)
                    drawSimple: zoomLevel < 12
                    z: 1000
                }
            }
        }


    }
    
    Image {
        id: targetIndicator
        source: "../data/target-indicator-cross.png"
        property variant t: getMappointFromCoord(showTargetAtLat, showTargetAtLon)
        x: map.x + t[0] - width/2
        y: map.y + t[1] - height/2

        visible: showTargetIndicator
        transform: Rotation {
            id: rotationTarget
            origin.x: targetIndicator.width/2
            origin.y: targetIndicator.height/2
        }
        /*
        NumberAnimation {
            running: true
            target: rotationTarget;
            property: "angle";
            from: 0;
            to: 359;
            duration: 2000
            loops: Animation.Infinite
        }*/

    }

    Rectangle {
        id: positionErrorIndicator
        visible: showCurrentPosition && settings.optionsShowPositionError
        width: currentPositionError * (1/getMetersPerPixel(currentPositionLat)) * 2
        height: width
        color: "#300000ff"
        border.width: 2
        border.color: "#800000ff"
        x: map.x + positionIndicator.t[0] - width/2
        y: map.y + positionIndicator.t[1] - height/2
        radius: width/2
    }

    Image {
        id: positionIndicator
        source: currentPositionValid ? "../data/position-indicator.png" : "../data/position-indicator-red.png"
        property variant t: getMappointFromCoord(currentPositionLat, currentPositionLon)
        x: map.x + t[0] - width/2
        y: map.y + t[1] - height + positionIndicator.width/2
        smooth: true

        visible: showCurrentPosition
        transform: Rotation {
            origin.x: positionIndicator.width/2
            origin.y: positionIndicator.height - positionIndicator.width/2
            angle: currentPositionAzimuth
        }
    }

    Rectangle {
        id: scaleBar
        anchors.right: parent.right
        anchors.rightMargin: 16
        anchors.topMargin: 16
        anchors.top: parent.top
        color: "black"
        border.width: 2
        border.color: "white"
        smooth: false
        height: 4
        width: scaleBarLength[0]
    }

    Text {
        text: F.formatDistance(scaleBarLength[1], settings)
        anchors.horizontalCenter: scaleBar.horizontalCenter
        anchors.top: scaleBar.bottom
        anchors.topMargin: 8
        style: Text.Outline
        styleColor: "white"
        font.pixelSize: 24
    }

    /*
    onCornerTileYChanged: {
        updateGeocaches();
    }

    onCornerTileXChanged: {
        updateGeocaches();
    }*/

    function updateGeocaches () {
        console.debug("Update geocaches called")
        if (zoomLevel < minZoomLevelShowGeocaches) {
            tooManyPoints = true
            //geocacheDisplay.model = emptyList
        } else {
            var from = getCoordFromScreenpoint(0,0)
            var to = getCoordFromScreenpoint(pinchmap.width,pinchmap.height)
            tooManyPoints = controller.getGeocaches(geocacheDisplay, from[0], from[1], to[0], to[1]);
        }
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
            if (rotationEnabled) {
                rot.angle = p.rotation
            }
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
        property int __firstX: -1;
        property int __firstY: -1;
        property bool __wasClick: false;
        property int maxClickDistance: 100;

        anchors.fill : parent;

        onPressed: {
            __isPanning = true;
            __lastX = mouse.x;
            __lastY = mouse.y;
            __firstX = mouse.x;
            __firstY = mouse.y;
            __wasClick = true;
        }

        onReleased: {
            __isPanning = false;
            if (! __wasClick) {
                panEnd();
            } else {
                var n = mousearea.mapToItem(geocacheDisplayContainer, mouse.x, mouse.y)
                var g = geocacheDisplayContainer.childAt(n.x, n.y)
                if (g != null) {
                    showAndResetDetailsPage()
                    controller.geocacheSelected(g.cache)
                }
            }

        }

        onPositionChanged: {
            if (__isPanning) {
                var dx = mouse.x - __lastX;
                var dy = mouse.y - __lastY;
                pan(-dx, -dy);
                __lastX = mouse.x;
                __lastY = mouse.y;
                /*
                once the pan threshold is reached, additional checking is unnecessary
                for the press duration as nothing sets __wasClick back to true
                */
                if (__wasClick && Math.pow(mouse.x - __firstX, 2) + Math.pow(mouse.y - __firstY, 2) > maxClickDistance) {
                    __wasClick = false;
                }
            }
        }

        onCanceled: {
            __isPanning = false;
        }
    }
}
