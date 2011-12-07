import QtQuick 1.0
import com.nokia.meego 1.0
import "uiconstants.js" as UI

Item {
    property alias text: titleText.text
    property alias color: rect.color

    Rectangle {
        id: rect
        width: parent.width
        /*x: parent.x - 30
        height: 80
        y: -25*/
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 66
    }
    Label {
        id: titleText
        font.pixelSize: UI.FONT_LARGE
        wrapMode: Text.Wrap
        width: parent.width
        color: UI.COLOR_HIGHLIGHT_TEXT
        //font.family: "Helvetica Nokia Pure"
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 16
        font.weight: Font.Light
    }
    anchors.top: parent.top
    anchors.left: parent.left
    anchors.right: parent.right
    height: titleText.height + 32
    anchors.bottomMargin: 16
}
