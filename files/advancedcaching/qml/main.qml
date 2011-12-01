import QtQuick 1.1
import com.nokia.meego 1.0
import "uiconstants.js" as UI
import QtMobility.sensors 1.2
import QtMobility.location 1.1

PageStackWindow {
    //property variant controller
    property variant geocacheList: 0
    property variant currentGeocache: 0
    property variant currentGeocacheCoordinates: 0
    property variant currentGeocacheLogs: 0
    property string downloadText: ""


    function showMessage (message) {
        banner.text = message
        banner.show()
    }

    function showProgress (progress, message) {
        progressBanner.text = message
        progressBanner.value = progress
        progressBanner.show()
    }

    function hideProgress () {
        progressBanner.hide()
    }

    function setGeocacheList (map, list) {
        map.model = list
    }

    function setCurrentGeocache(geocache, coordinates, logs) {
        currentGeocache = geocache;
        currentGeocacheCoordinates = coordinates; //currentGeocache.coordinates;
        currentGeocacheLogs = logs;
        //console.log(coordinates)
        //console.debug("Current Cache size "+geocache.size+" terrain "+geocache.terrain+" difficulty "+geocache.difficulty+" owner "+geocache.owner+" and has "+currentGeocacheCoordinates.count + " WPs")
    }

    id: rootWindow


    initialPage: MainPage {
        id: mainPage
    }


    InfoBanner {
        id: banner
    }

    ProgressBanner {
        id: progressBanner
    }

    Compass {
        id: compass
        onReadingChanged: {azimuth = compass.reading.azimuth; calibration = compass.reading.calibrationLevel; }
        property real azimuth: 0
        property real calibration: 0
        active: true
    }

    PositionSource {
        id: gpsSource
        active: true
        updateInterval: 500
        onPositionChanged: {
            console.log("Changed!");
            console.log("pos: " + gpsSource.position.latitudeValid + " and " + position.coordinate.latitude);
            console.log(position.latitudeValid +" | "+ position.coordinate.latitude+" | "+ position.coordinate.longitude+" | "+ position.altitudeValid+" | "+ position.coordinate.altitude+" | "+ position.speedValid+" | "+ position.speed+" | "+ position.horizontalAccuracy)
            controller.positionChanged(position.latitudeValid, position.coordinate.latitude, position.coordinate.longitude, position.altitudeValid, position.coordinate.altitude, position.speedValid, position.speed, position.horizontalAccuracy, position.timestamp);
        }
    }

    DetailsDefaultPage {
        id: pageDetailsDefault
    }
    DescriptionPage {
        id: pageDescription
    }
    LogsPage {
        id: pageLogs
    }

    CoordinatesPage {
        id: pageCoordinates
    }

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
