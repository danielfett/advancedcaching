import QtQuick 1.1
import com.nokia.meego 1.0
import "uiconstants.js" as UI
import Qt.labs.components 1.0


Page {
    id: listPage
    tools: commonTools

    TabGroup {
        id: tabGroup
        currentTab: tabMap
        CompassPage {
            id: tabCompass
        }

        Page {
            id: tabMap
            PinchMap {
                id: pinchmap
                anchors.fill: parent
                model: geocacheList
                centerLatitude: gps.lastGoodFix.lat;
                centerLongitude: gps.lastGoodFix.lon;
                zoomLevel: 11
            }
            Row {
                anchors.bottom: pinchmap.bottom
                anchors.bottomMargin: 16
                anchors.right: pinchmap.right
                anchors.rightMargin: 16
                spacing: 16
                property int buttonSize: 72
                Button {
                    iconSource: "image://theme/icon-m-common-add"
                    onClicked: {pinchmap.zoomIn() }
                    width: parent.buttonSize
                    height: parent.buttonSize
                }
                Button {
                    iconSource: "image://theme/icon-m-common-remove"
                    onClicked: {pinchmap.zoomOut() }
                    width: parent.buttonSize
                    height: parent.buttonSize
                }
            }
            Row {
                anchors.bottom: pinchmap.bottom
                anchors.bottomMargin: 16
                anchors.left: pinchmap.left
                anchors.leftMargin: 16
                spacing: 16
                property int buttonSize: 72
                Button {
                    iconSource: "image://theme/icon-m-common-location"
                    onClicked: {pinchmap.setCenterLatLon(48.85568,2.386093) }
                    width: parent.buttonSize
                    height: parent.buttonSize
                    checkable: true

                }
            }
        }
        PageStack {
            id: tabDetailsPageStack
            anchors.fill: parent
            Component.onCompleted: {
                push(pageDetailsDefault)
                pageDetailsDefault.buttonClicked.connect(function(t) {
                                                             if (t == "DescriptionPage") push(pageDescription);
                                                             if (t == "CoordinatesPage") push (pageCoordinates);
                                                             if (t == "LogsPage") push (pageLogs);
                                                             if (t == "ImagesPage") push (pageImages);
                                                             if (t == "CacheCalcPage") push (pageCacheCalc);
                                                         } )
            }
        }
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
    }



    ToolBarLayout {
        id: commonTools
        visible: true
        ToolIcon {
            iconId: "toolbar-back"
            onClicked: {
                if (tabDetailsPageStack.depth > 1) tabDetailsPageStack.pop();
            }
        }

        ButtonRow {
            style: TabButtonStyle { }
            TabButton {
                text: "Compass"
                tab: tabCompass
            }
            TabButton {
                text: "Map"
                tab: tabMap
            }
            TabButton {
                text: "Details"
                tab: tabDetailsPageStack
            }
            TabButton {
                //text: "Settings"
                tab: tabSettings
                iconSource: "image://theme/icon-m-toolbar-view-menu"
            }
        }
    }
}
