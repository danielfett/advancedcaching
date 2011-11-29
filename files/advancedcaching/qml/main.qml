import QtQuick 1.1
import com.nokia.meego 1.0
import com.nokia.extras 1.0
import "uiconstants.js" as UI
import QtMobility.sensors 1.2
import QtMobility.location 1.1

PageStackWindow {
    //property variant controller
    property variant geocacheList: 0
    property variant currentGeocache: 0
    property variant currentGeocacheCoordinates: 0
    property real downloadProgress: 0.5
    property bool downloadShowProgress: false
    property string downloadText: ""

    function showMessage (message) {
        banner.text = message
        banner.show()
    }

    function showProgress (progress, message) {
        downloadProgress = progress
        downloadShowProgress = true
        downloadText = message
        showMessage(message)
    }

    function hideProgress () {
        downloadShowProgress = false
    }

    function setGeocacheList (map, list) {
        map.model = list
    }

    function setCurrentGeocache(geocache, coordinates) {
        currentGeocache = geocache;
        currentGeocacheCoordinates = coordinates; //currentGeocache.coordinates;
        //console.log(coordinates)
        console.debug("Current Cache size "+geocache.size+" terrain "+geocache.terrain+" difficulty "+geocache.difficulty+" owner "+geocache.owner+" and has "+currentGeocacheCoordinates.count + " WPs")
    }

    id: rootWindow


    initialPage: MainPage {
        id: mainPage
    }


    InfoBanner {
        id: banner
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
            controller.positionChanged(position)
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
        property real gpspos: gps.data.lat
        onGpsposChanged: {
            console.log(gpspos)
        }
    }
}
