import QtQuick 1.1
import com.nokia.meego 1.0
import "uiconstants.js" as UI

Page {
    id: tabImages
    orientationLock: PageOrientation.LockPortrait
    width: parent.width
    GeocacheHeader{
        cache: currentGeocache
        id: header
    }
    Flickable {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: 16
        anchors.rightMargin: 16
        anchors.top: header.bottom
        anchors.bottom: parent.bottom
        contentWidth: width
        contentHeight: col1.height * 3
        clip: true

        Column {
            id: col1
            anchors.left: parent.left
            anchors.right: parent.right

            Grid {
                anchors.left: parent.left
                anchors.right: parent.right
                columns: 3
                spacing: 8
                Repeater {
                    model: currentGeocache.varList || emptyList
                    delegate: Row {
                        Label {
                            id: label
                            text: "" + model.vars.char + "="
                            width: 45
                            font.pixelSize: 28
                            anchors.verticalCenter: labelText.verticalCenter
                        }
                        TextField {
                            placeholderText: "?"
                            width: 90
                            id: labelText
                            text: "" + model.vars.value
                            font.pixelSize: 28
                            onTextChanged: {
                                model.vars.value = text
                            }
                            inputMethodHints: Qt.ImhFormattedNumbersOnly
                        }
                    }
                }
            }

            Repeater {
                width: parent.width
                model: currentGeocache.calcCoordinates || emptyList
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
                                text: model.coordinate.source || "Unknown Source"
                                font.weight: Font.Bold
                                font.pixelSize: 26
                                width: col1.width - arrow.width
                                wrapMode: Text.WordWrap
                            }

                            Label {
                                id: subText
                                text: model.coordinate.originalText
                                font.weight: Font.Light
                                font.pixelSize: 22
                                color: theme.inverted ? UI.COLOR_DESCRIPTION_NIGHT : UI.COLOR_DESCRIPTION
                                visible: text != ""
                                width: col1.width - arrow.width
                                wrapMode: Text.WordWrap
                            }

                            Label {
                                id: subText2
                                text: model.coordinate.text
                                font.weight: Font.Light
                                font.pixelSize: 22
                                color: theme.inverted ? UI.COLOR_DESCRIPTION_NIGHT : UI.COLOR_DESCRIPTION
                                visible: text != ""
                                width: col1.width - arrow.width
                                wrapMode: Text.WordWrap
                            }

                            Label {
                                id: warnings
                                text: model.coordinate.warnings
                                font.weight: Font.Light
                                font.pixelSize: 22
                                color: "yellow"
                                visible: text != ""
                                width: col1.width - arrow.width
                                wrapMode: Text.WordWrap
                            }
                        }
                    }

                    Image {
                        id: arrow
                        source: "image://theme/icon-m-common-drilldown-arrow" + (theme.inverted ? "-inverse" : "")
                        anchors.right: parent.right;
                        anchors.verticalCenter: parent.verticalCenter
                    }

                    MouseArea {
                        id: mouseArea
                        anchors.fill: background
                        onClicked: {

                        }
                    }
                    height: r.height + 16
                    width: parent.width
                }
            }




        }

    }
}

