import QtQuick 1.1
import com.nokia.meego 1.0
import "uiconstants.js" as UI
import QtMobility.sensors 1.2
import QtMobility.location 1.1

PageStackWindow {
    //property variant controller
    property variant geocacheList: 0
    property variant currentGeocache: null
    property string downloadText: ""


    function setGeocacheList(map, l) {
        map.model = l
    }

    function showMessage (message) {
        banner.text = message
        banner.show()
        return;
    }

    Connections {
        target: controller
        onProgressChanged: {
            if (controller.progressVisible) {
                progressBanner.show()
            } else {
                progressBanner.hide()
            }
        }
    }

    function setCurrentGeocache(geocache) {
        currentGeocache = geocache;
        settings.lastSelectedGeocache = geocache.name;
    }

    id: rootWindow


    initialPage: MainPage {
        id: mainPage
    }


    ListModel {
        id: emptyList
    }

    InfoBanner {
        id: banner
    }

    ProgressBanner {
        id: progressBanner
        text: controller.progressMessage
        value: controller.progress
    }

    Compass {
        id: compass
        onReadingChanged: {azimuth = compass.reading.azimuth; calibration = compass.reading.calibrationLevel; }
        property real azimuth: 0
        property real calibration: 0
        active: true
        dataRate: 10
    }

    PositionSource {
        id: gpsSource
        active: true
        updateInterval: 1000
        onPositionChanged: {
            console.log("Changed!");
            console.log("pos: " + gpsSource.position.latitudeValid + " and " + position.coordinate.latitude);
            console.log(position.latitudeValid +" | "+ position.coordinate.latitude+" | "+ position.coordinate.longitude+" | "+ position.altitudeValid+" | "+ position.coordinate.altitude+" | "+ position.speedValid+" | "+ position.speed+" | "+ position.horizontalAccuracy)
            controller.positionChanged(position.latitudeValid, position.coordinate.latitude, position.coordinate.longitude, position.altitudeValid, position.coordinate.altitude, position.speedValid, position.speed, position.horizontalAccuracy, position.timestamp);
        }
    }

    function showDetailsPage(page) {
        mainPage.showDetailsPage(page)
    }



    /*
    CoordinatesPage {
        id: pageCoordinates
    }*/

    /*
    Accelerometer {
        id: accelerometer
        onReadingChanged: {
            //console.log("                    x: "+accelerometer.reading.x+" y: "+accelerometer.reading.y+" z: " + accelerometer.reading.z)
            var divider = Math.sqrt(Math.pow(accelerometer.reading.x,2) + Math.pow(accelerometer.reading.y, 2) + Math.pow(accelerometer.reading.z, 2) )
            accelerometer.x = Math.acos(accelerometer.reading.x / divider) * (180.0/Math.PI) - 90
            accelerometer.y = Math.acos(accelerometer.reading.y / divider) * (180.0/Math.PI) - 90
            accelerometer.z = Math.acos(accelerometer.reading.z / divider) * (180.0/Math.PI)
            //console.log("X: " + accelerometer.x + ", Y: " + accelerometer.y + ", Z: " + accelerometer.z)
        }
        property int x: 0
        property int y: 0
        property int z: 0
        active: true
    }*/
    CoordinateSelector {
        id: coordinateSelectorDialog
    }
}
