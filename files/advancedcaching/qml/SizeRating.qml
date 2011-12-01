import QtQuick 1.1
import "uiconstants.js" as UI

Item {
    property int size: 0
    property alias text: title.text
    Text {
        id: title
        font.pixelSize: 20
        y: 0
        color: UI.COLOR_INFOLABEL
        font.weight: Font.Bold
    }
    Image {
        id: micro
        source: "../data/icon-micro" + (size == 1 ? "-active" : "") + ".png"
        y: 26
    }
    Image {
        id: small
        source: "../data/icon-small" + (size == 2 ? "-active" : "") + ".png"
        y: 26
        anchors.left: micro.right
    }
    Image {
        id: regular
        source: "../data/icon-regular" + (size == 3 ? "-active" : "") + ".png"
        y: 26
        anchors.left: small.right
    }
    Image {
        id: large
        source: "../data/icon-large" + (size == 4 ? "-active" : "") + ".png"
        y: 26
        anchors.left: regular.right
    }
    Image {
        id: unknown
        source: "../data/icon-unknown" + ((size < 1 || size > 4)  ? "-active" : "") + ".png"
        y: 26
        anchors.left: large.right
    }

    height: micro.height + 26
    anchors.topMargin: 16
    width: 5 * micro.width
}
