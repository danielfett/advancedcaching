import QtQuick 1.0
import "uiconstants.js" as UI

Rectangle {
    property alias text: label.text

    width: parent.width
    height: label.height + 2*16
    signal clicked

    Text{
        id: label
        anchors.verticalCenter: parent.verticalCenter
        anchors.left: parent.left
        anchors.leftMargin: 16
        font.pixelSize: UI.FONT_DEFAULT
        text: "Click me"
    }
    Image {
        source: "image://theme/icon-s-common-next"
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        anchors.rightMargin: 16
    }
    MouseArea {
        id: mouse
        anchors.fill:  parent
        onClicked: parent.clicked()
    }

    color: mouse.pressed ? "#c0c0c0" : "transparent"
}
