import QtQuick 1.0
import "uiconstants.js" as UI
import com.nokia.meego 1.0

Item {
    property alias text: label.text

    width: parent.width
    height: label.paintedHeight + 24
    signal clicked


    BorderImage {
        id: background
        anchors.fill: parent
        // Fill page borders
        anchors.leftMargin: -16
        anchors.rightMargin: -16
        visible: mouse.pressed
        source: "image://theme/meegotouch-list-background-pressed-center"
    }

    Label {
        id: label
        //font.weight: Font.Bold
        anchors.verticalCenter: parent.verticalCenter
        anchors.left: parent.left
        anchors.leftMargin: 16
        font.pixelSize: UI.FONT_DEFAULT
        text: "Click me"
    }
    Image {
        source: "image://theme/icon-m-common-drilldown-arrow" + (theme.inverted ? "-inverse" : "")
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        anchors.rightMargin: 16
    }
    MouseArea {
        id: mouse
        anchors.fill:  parent
        onClicked: parent.clicked()
    }
}
