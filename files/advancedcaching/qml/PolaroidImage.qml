import QtQuick 1.1
import com.nokia.meego 1.0
import "uiconstants.js" as UI

Rectangle {
    color: "white"
    border.width: 2
    border.color: "#c0c0c0"
    property alias source: image.source
    property alias text: text.text
    Image {
        id: image
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margin: 16
        smooth: true
    }
    smooth: true
    
    Label {
        id: text
        wrapMode: Text.Wrap
        anchors.left: image.left
        anchors.right: image.right
        anchors.top: image.top
        anchors.topMargin: 20
    }
    
    height: image.margin + image.height + 2 * text.anchors.topMargin + text.paintedHeight
    width: image.width + 2*image.margin
}
        
