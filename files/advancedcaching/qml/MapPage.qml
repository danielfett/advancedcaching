import QtQuick 1.1
import com.nokia.meego 1.0
import "uiconstants.js" as UI


Page {
    id: tabMap
    property int buttonSize: 72

    orientationLock: PageOrientation.LockPortrait

    PinchMap {
        id: pinchmap
        anchors.fill: parent
        model: geocacheList
        centerLatitude: (followPositionButton.checked && gps.lastGoodFix.valid) ? gps.lastGoodFix.lat : controller.mapPositionLat
        centerLongitude: (followPositionButton.checked && gps.lastGoodFix.valid) ? gps.lastGoodFix.lon : controller.mapPositionLon
        zoomLevel: controller.mapZoom || 11
        onLatitudeChanged: {
            controller.updateSetting('map_position_lat', latitude.toString());
        }

        onLongitudeChanged: {
            controller.updateSetting('map_position_lon', longitude.toString());
        }

        onZoomLevelChanged: {
            controller.updateSetting('map_zoom', zoomLevel.toString());
        }
        showTargetIndicator: gps.targetValid;
        showTargetAtLat: gps.target.lat || 0
        showTargetAtLon: gps.target.lon || 0
        // Rotating the map for fun and profit.
        // angle: -compass.azimuth
        showCurrentPosition: true
        currentPositionValid: gps.hasFix
        currentPositionLat: gps.lastGoodFix.lat
        currentPositionLon: gps.lastGoodFix.lon
        currentPositionAzimuth: compass.azimuth

    }

    Image {
        id: compassImage
        source: "../data/windrose-simple.svg"
        transform: [Rotation {
                id: azCompass
                origin.x: compassImage.width/2
                origin.y: compassImage.height/2
                angle: -compass.azimuth
            }]
        anchors.left: tabMap.left
        anchors.leftMargin: 16
        anchors.top: tabMap.top
        anchors.topMargin: 16
        smooth: true
        width: Math.min(tabMap.width/4, tabMap.height/4)
        fillMode: Image.PreserveAspectFit
        z: 2

        Image {
            property int angle: gps.targetBearing || 0
            property int outerMargin: 0
            id: arrowImage
            visible: (gps.targetValid && gps.lastGoodFix.valid)
            source: "../data/arrow_target.svg"
            width: (compassImage.paintedWidth / compassImage.sourceSize.width)*sourceSize.width
            fillMode: Image.PreserveAspectFit
            x: compassImage.width/2 - width/2
            y: arrowImage.outerMargin
            z: 3
            transform: Rotation {
               origin.y: compassImage.height/2 - arrowImage.outerMargin
               origin.x: arrowImage.width/2
               angle: arrowImage.angle
           }
        }
    }

    Row {
        id: buttonsRight
        anchors.bottom: pinchmap.bottom
        anchors.bottomMargin: 16
        anchors.right: pinchmap.right
        anchors.rightMargin: 16
        spacing: 16
        Button {
            iconSource: "image://theme/icon-m-common-add"
            onClicked: {pinchmap.zoomIn() }
            width: parent.parent.buttonSize
            height: parent.parent.buttonSize
        }
        Button {
            iconSource: "image://theme/icon-m-common-remove"
            onClicked: {pinchmap.zoomOut() }
            width: parent.parent.buttonSize
            height: parent.parent.buttonSize
        }
    }
    Column {
        id: buttonsLeft
        anchors.bottom: pinchmap.bottom
        anchors.bottomMargin: 16
        anchors.left: pinchmap.left
        anchors.leftMargin: 16
        spacing: 16
        Button {
            id: followPositionButton
            iconSource: "image://theme/icon-m-common-location"
            //onClicked: {pinchmap.setCenterLatLon(48.85568,2.386093) }
            width: parent.parent.buttonSize
            height: parent.parent.buttonSize
            checkable: true

        }
        Button {
            id: refreshGeocachesButton
            iconSource: "image://theme/icon-m-toolbar-refresh"
            width: parent.parent.buttonSize
            height: parent.parent.buttonSize
            onClicked: {
                pinchmap.requestUpdate()
            }
        }
        Button {
            id: settingsButton
            iconSource: "image://theme/icon-m-toolbar-view-menu"
            width: parent.parent.buttonSize
            height: parent.parent.buttonSize
            onClicked: {
                mapMenu.open()
            }
        }
    }
    ProgressBar {
        id: zoomBar
        anchors.bottom: buttonsLeft.top;
        anchors.bottomMargin: 16;
        anchors.left: buttonsLeft.left;
        anchors.right: buttonsRight.right;
        maximumValue: pinchmap.maxZoomLevel;
        minimumValue: pinchmap.minZoomLevel;
        value: pinchmap.zoomLevel;
        visible: false
        Behavior on value {
            SequentialAnimation {
                PropertyAction { target: zoomBar; property: "visible"; value: true }
                NumberAnimation { duration: 100; }
                PauseAnimation { duration: 750; }
                PropertyAction { target: zoomBar; property: "visible"; value: false }
            }
        }
    }
    Menu {
         id: mapMenu
         visualParent: tabMap

         MenuLayout {
             MenuItem { text: "Fetch Details for all in view"; onClicked: { pinchmap.requestUpdateDetails() } }
             MenuItem { text: "Reload Map"; onClicked: { pinchmap.populate(); } }
             MenuItem { text: "Use Center as Target"; onClicked: {
                     var c = pinchmap.getCenter();
                     controller.setTarget(c[0], c[1]);
                 }}
         }
     }
}
