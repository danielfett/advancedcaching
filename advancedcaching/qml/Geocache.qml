import QtQuick 1.0
import "uiconstants.js" as UI

Rectangle {
    width: drawSimple ? 10: 36
    height: drawSimple ? 10: 36
    property variant cache
    property variant targetPoint
    property bool drawSimple
    x: targetPoint[0] - width/2
    y: targetPoint[1] - height/2
    color: (currentGeocache && cache.name == currentGeocache.name) ? "#44ff0000" : (cache.marked ? "#88ffff80" : "#88ffffff")
    border.width: 4
    border.color: UI.getCacheColor(cache)
    //smooth: true
    radius: 7
    visible: ! (settings.optionsHideFound && cache.found)
    Image {
        source: (cache.status == 0) ? "../data/mark.png" : "../data/cross.png";
        anchors.centerIn: parent
        visible: ! drawSimple
    }
}
