import QtQuick 1.0
import com.nokia.meego 1.0
import "uiconstants.js" as UI

Page {
    Header{
        text: "Geocache <b>GCEZ71U</b>"
        id: header
    }

    signal buttonClicked (string target)

    Column {
        id: col1
        anchors.top: header.bottom
        spacing: 16
        anchors.left: parent.left
        anchors.right:  parent.right
        anchors.leftMargin: 16
        anchors.rightMargin: 16

        Text {
            wrapMode: Text.Wrap
            font.pixelSize: UI.FONT_DEFAULT
            text: "Dies ist der lange Titel eines verhängnisvollen Geocaches"
            width: parent.width
        }

        Row {
            width: parent.width
            StarRating{
                id: rating1
                rating: 5
                text: "Terrain"
                //anchors.top: title.bottom
            }
            StarRating{
                id: rating2
                rating: 2
                anchors.right: parent.right
                text: "Difficulty"
            }
        }
        Row {
            width: parent.width
            SizeRating {
                id: rating3
                size: 2
                text: "Size"
                //anchors.top: title.bottom
            }

            InfoLabel {
                name: "Created by"
                value: "Christian Test"
                anchors.right: parent.right
            }
        }
        Row {
            width: parent.width

            InfoLabel {
                name: "Status"
                value: "active"
            }

            InfoLabel {
                name: "Created"
                value: "2010-08-13"
                anchors.right: parent.right
            }
        }
    }

    Column {
        anchors.bottom: parent.bottom
        spacing: 0
        width: parent.parent.width

        ListButton {
            text: "Description"
            onClicked: {
                parent.parent.buttonClicked("DescriptionPage")
            }

        }


        ListButton {
            text: "Coordinates"
            onClicked: {
                parent.parent.buttonClicked("CoordinatesPage")
            }
        }

        ListButton {
            text: "Logs (3)"
            // todo: Add Icons of Logs here

            onClicked: {
                parent.parent.buttonClicked("LogsPage")
            }
        }

        ListButton {
            text: "Images (4)"
            onClicked: {
                parent.parent.buttonClicked("ImagesPage")
            }
        }

        ListButton {
            text: "CacheCalc"

            onClicked: {
                parent.parent.buttonClicked("CacheCalcPage.qml")
            }
        }

/*
        Flickable {
            WebView {
                id: description
                html: "Dies ist ein <b>Test</b>. Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. At vero eos et accusam et justo duo dolores et ea rebum. Stet clita kasd gubergren, no sea takimata sanctus est Lorem ipsum dolor sit amet. Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. At vero eos et accusam et justo duo dolores et ea rebum. Stet clita kasd gubergren, no sea takimata sanctus est Lorem ipsum dolor sit amet."
                settings.javascriptEnabled: false
                settings.javaEnabled: false
                settings.defaultFontSize: 25
                width: parent.parent.width// parent.width
                height: 300
            }

            height: 200
            width: parent.width
            contentWidth: description.width
            contentHeight: description.height
        }
*/

    }
}
