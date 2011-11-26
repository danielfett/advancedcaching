import QtQuick 1.1
import com.nokia.meego 1.0
import "uiconstants.js" as UI
import QtMobility.sensors 1.2

PageStackWindow {
    //platformStyle.screenOrientation: "portrait";
    id: rootWindow
    //property int pageMargin: 16

    // ListPage is what we see when the app starts, it links to
    // the component specific pages
    initialPage: MainPage { }

    // These tools are shared by most sub-pages by assigning the
    // id to a page's tools property
    //platformStyle: PageStackWindowStyle {
    //    background: COLOR_BACKGROUND
    //}
    
    Compass {
        id: compass
        onReadingChanged: {azimuth = compass.reading.azimuth; calibration = compass.reading.calibrationLevel; }
        property real azimuth: 0
        property real calibration: 0
        active: true
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
}
