import QtQuick 1.0
import "uiconstants.js" as UI

Rectangle {
    id: geocacheRectangle
    width: drawSimple ? 10: 36
    height: drawSimple ? 10: 36
    property variant cache
    property variant targetPoint
    property bool drawSimple
    x: targetPoint[0] - width/2
    y: targetPoint[1] - height/2
    color: (cache.name == currentGeocache.name) ? "#88ff0000" : "#88ffffff"
    border.width: 4
    border.color: UI.getCacheColor(cache)
    //smooth: true
    radius: 7
    visible: ! (settings.optionsHideFound && cache.found)
    Image {
        source: "../data/cross.svg"
        anchors.centerIn: parent
        visible: ! drawSimple
    }
    /*
    Text {
        font.pixelSize: 15
        font.weight: Font.Bold
        text: cache.title
        width: 150
        wrapMode: Text.WordWrap
        anchors.left: parent.right
        anchors.leftMargin: 8
        color: "green"
        visible: ! drawSimple
    }*/
}
