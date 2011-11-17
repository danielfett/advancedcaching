
import com.nokia.meego 1.0
import com.nokia.meego 1.0 as Nokia
import QtQuick 1.1
import "uiconstants.js" as UI

QueryDialog {
    id: test
    //content: [CoordinateSelector{ anchors.centerIn: parent }]
    anchors.centerIn: parent
    //title: [Text{ text: "Test!"; font.pixelSize: UI.FONT_LARGE; color: "white"} ]
    titleText: "Testtext"

    content: [Column {
        // Longitude
        Row {
            Button {
                text: "N"
                font.pixelSize: UI.FONT_LARGE
                onClicked: { text = ((text == "N") ? "S" : "N") }
                anchors.verticalCenter: parent.verticalCenter
                width: UI.WIDTH_SELECTOR
            }
            UpDownSelect {
                id: lon1
                max: 1
            }

            UpDownSelect {
                id: lon2
            }

            UpDownSelect {
                id: lon3
            }
            Text {
                text: "."
                font.pixelSize:  UI.FONT_LARGE
                anchors.verticalCenter: parent.verticalCenter
            }

            UpDownSelect {
                id: lon4
            }

            UpDownSelect {
                id: lon5
            }

            Rectangle {
                height: 30
                color: "transparent"
                width: UI.WIDTH_SELECTOR/3
            }

            UpDownSelect {
                id: lon6
            }

            UpDownSelect {
                id: lon7
            }

            UpDownSelect {
                id: lon8
            }
        }
        Row {
            Button {
                text: "W"
                font.pixelSize: UI.FONT_LARGE
                onClicked: { text = ((text == "W") ? "E" : "W") }
                width: UI.WIDTH_SELECTOR
                anchors.verticalCenter: parent.verticalCenter
            }
            UpDownSelect {
                id: lat1
                max: 1
            }

            UpDownSelect {
                id: lat2
            }

            Text {
                text: "."
                font.pixelSize:  UI.FONT_LARGE
            }

            UpDownSelect {
                id: lat3
            }

            UpDownSelect {
                id: lat4
            }

            Rectangle {
                height: 30
                color: "transparent"
                width: UI.WIDTH_SELECTOR/3
            }

            UpDownSelect {
                id: lat5
            }

            UpDownSelect {
                id: lat6
            }

            UpDownSelect {
                id: lat7
            }
        }
    }]
}
