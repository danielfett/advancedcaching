import QtQuick 1.0
import com.nokia.meego 1.0
import "uiconstants.js" as UI

Page {
    Header{
        text: "Geocache <b>" + (currentGeocache ? currentGeocache.name : "(none)") + "</b>"
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
            text: currentGeocache ? currentGeocache.title : ""
            width: parent.width
        }

        InfoLabel {
            name: "Created by"
            value: currentGeocache.owner || "unknown"
            width: col1.width
        }

        Item {
            height: Math.max(col1col1.height, col1col2.height)
            width: parent.width
            Column {
                id: col1col1
                anchors.left: parent.left
                anchors.top: parent.top
                width: parent.width/2
                spacing: 16
                StarRating{
                    id: rating1
                    rating: currentGeocache.terrain || -1
                    text: "Terrain"
                }
                SizeRating {
                    id: rating3
                    size: currentGeocache.size || -1
                    text: "Size"
                }
            }
            Column {
                id: col1col2
                anchors.top: parent.top
                anchors.right: parent.right
                spacing: 16
                StarRating{
                    id: rating2
                    rating: currentGeocache.difficulty || -1
                    text: "Difficulty"
                }
                InfoLabel {
                    name: "Status"
                    value: "active"
                }
                /*
                InfoLabel {
                    name: "Created"
                    value: "2010-08-13?"
                }*/
                Button {
                    text: "Fetch details"
                    onClicked: {
                        controller.geocacheDownloadDetailsClicked(currentGeocache)
                    }
                    width: col1.width/2
                }
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

    }
}
