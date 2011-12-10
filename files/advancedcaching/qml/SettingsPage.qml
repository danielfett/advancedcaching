import QtQuick 1.1
import com.nokia.meego 1.0
import "uiconstants.js" as UI
import "functions.js" as F

Page {
    id: tabSettings
    Header {
        text: "Settings"
        id: header
        color: "grey"
    }

    Column {
        anchors.top: header.bottom
        anchors.leftMargin: 16
        anchors.rightMargin: 16
        anchors.left: parent.left
        anchors.right: parent.right

        spacing: 16
        Label {
            font.pixelSize: 20
            color: UI.COLOR_INFOLABEL
            text: "geocaching.com user data"
        }

        TextField {
            placeholderText: "username"
            width: parent.width
            id: inputUsername
            text: settings.optionsUsername
        }
        TextField {
            placeholderText: "password"
            width: parent.width
            id: inputPassword
            echoMode: TextInput.PasswordEchoOnEdit
            text: settings.optionsPassword
        }
        Button {
            anchors.right: parent.right
            text: "save"
            onClicked: {
                var pw = inputPassword.text;
                var un = inputUsername.text;
                settings.optionsPassword = pw
                settings.optionsUsername = un
            }
        }
        
        Label {
            font.pixelSize: 20
            color: UI.COLOR_INFOLABEL
            text: "Map Type"
        }

        Flow {
            Repeater {
                model: settings.mapTypes || emptyList
                delegate: Rectangle {
                            //text: model.maptype.url
                            Image {
                                source: F.getMapTile(model.maptype.url, 8811, 5378, 14);
                                width: 128;
                                height: 128;
                                anchors.centerIn: parent
                                fillMode: Image.Tile
                            }
                            width: 132;
                            height: 132;
                            color: (model.maptype == settings.currentMapType) ? 'red' : 'grey'
                            MouseArea {
                                anchors.fill: parent
                                onClicked: {
                                    console.debug("Setting map type to index " + index)
                                    settings.currentMapType = model.maptype
                                }
                            }
                    }
            }
        }
        
        
        
        Label {
            font.pixelSize: 20
            color: UI.COLOR_INFOLABEL
            text: "Map View"
        }
        
        Row {
            anchors.left: parent.left
            anchors.right: parent.right
            Label {
                 text: "Enable Map Rotation (BETA)"
                 font.weight: Font.Bold
                 font.pixelSize: 26
            }
            
            Switch {
                anchors.right: parent.right
                onCheckedChanged: {
                    settings.optionsMapRotation = checked
                }
                checked: settings.optionsMapRotation
            }
        }
        
        Row {
            anchors.left: parent.left
            anchors.right: parent.right
            Label {
                 text: "Hide Found Geocaches"
                 font.weight: Font.Bold
                 font.pixelSize: 26
            }
            
            Switch {
                anchors.right: parent.right
                onCheckedChanged: {
                    settings.optionsHideFound = checked
                }
                checked: settings.optionsHideFound
            }
        }
        
        Row {
            anchors.left: parent.left
            anchors.right: parent.right
            Label {
                 text: "Show position error on map"
                 font.weight: Font.Bold
                 font.pixelSize: 26
            }
            
            Switch {
                anchors.right: parent.right
                onCheckedChanged: {
                    settings.optionsShowPositionError = checked
                }
                checked: settings.optionsShowPositionError
            }
        }
        
    }

}
