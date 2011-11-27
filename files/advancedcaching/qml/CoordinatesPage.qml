import QtQuick 1.1
import com.nokia.meego 1.0
import "uiconstants.js" as UI

Page {
    id: listPage
    Header{
        text: "Geocache <b>"+currentGeocache.name+"</b>"
        id: listHeader
    }

    ListView {
        anchors.top: listHeader.bottom
        anchors.leftMargin: 16
        anchors.rightMargin: 16
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom:  parent.bottom
        model: currentGeocacheCoordinates
        delegate: Item {
            BorderImage {
                 id: background
                 anchors.fill: parent
                 anchors.leftMargin: -16
                 anchors.rightMargin: -16
                 visible: mouseArea.pressed
                 source: "image://theme/meegotouch-list-background-pressed-center"
             }

             Row {
                 id: r
                 anchors.verticalCenter: parent.verticalCenter
                 Column {

                     Label {
                         id: mainText
                         text: model.coordinate.display_text
                         font.weight: Font.Bold
                         font.pixelSize: 26
                     }

                     Label {
                         id: subText
                         text: model.coordinate.comment
                         font.weight: Font.Light
                         font.pixelSize: 22
                         color: UI.COLOR_DESCRIPTION
                         visible: text != ""
                     }

                     Label {
                         id: subCoordinate
                         text: model.coordinate.name
                         font.weight: Font.Light
                         font.pixelSize: 22
                         visible: text != ""
                     }
                 }
             }

             Image {
                 source: "image://theme/icon-m-common-drilldown-arrow" + (theme.inverted ? "-inverse" : "")
                 anchors.right: parent.right;
                 anchors.verticalCenter: parent.verticalCenter
             }

             MouseArea {
                 id: mouseArea
                 anchors.fill: background
                 onClicked: {
                     //listPage.openFile(page)
                 }
             }
             height: r.height + 16
             width: parent.width
        }
    }
}
