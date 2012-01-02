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
        Column {
            Flow {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.leftMargin: 16
                anchors.rightMargin: 16
                anchors.top: header.bottom
                spacing: 8
                Repeater {
                    model: currentGeocache.varList || emptyList
                    delegate:
                        Row {
                        Label {
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

        }

    }
}

