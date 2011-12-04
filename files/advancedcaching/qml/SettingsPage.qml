import QtQuick 1.1
import com.nokia.meego 1.0
import "uiconstants.js" as UI


Page {
    id: tabSettings
    Header {
        text: "Settings"
        id: header
    }

    Column {
        anchors.top: header.bottom
        anchors.leftMargin: 16
        anchors.rightMargin: 16
        anchors.left: parent.left
        anchors.right: parent.right

        spacing: 16
        Text {
            font.pixelSize: 20
            color: UI.COLOR_INFOLABEL
            text: "geocaching.com user data"
        }
        TextField {
            placeholderText: "username"
            width: parent.width
            id: inputUsername
            text: settings.username
        }
        TextField {
            placeholderText: "password"
            width: parent.width
            id: inputPassword
            echoMode: TextInput.PasswordEchoOnEdit
            text: settings.password
        }
        Button {
            anchors.right: parent.right
            text: "save"
            onClicked: {
                settings.password = inputPassword.text
                settings.username = inputUsername.text
            }
        }


        ListView {
            model: geocacheList
            delegate: Text {
                text: "Geocache " + model.title + " bei lat " + model.lat
            }
        }
    }

}
