import QtQuick 1.1
import com.nokia.meego 1.0
import "uiconstants.js" as UI
import "functions.js" as F

Page {
    id: listPage
    orientationLock: PageOrientation.LockPortrait
    GeocacheHeader{
        cache: currentGeocache
        id: listHeader
    }

    Flickable {
        anchors.top: listHeader.bottom
        anchors.leftMargin: 16
        anchors.rightMargin: 16
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom:  parent.bottom
        contentHeight: col1.height
        contentWidth: width
        clip: true

        Column {
            id: col1
            width: parent.width

            Label {
                font.pixelSize: 20
                color: UI.COLOR_INFOLABEL
                text: "Plain Coordinates"
            }

            Repeater {
                width: parent.width

                model: currentGeocache.coordinates || emptyList
                clip: true
                id: list
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
                                text: model.coordinate.name || "No Title"
                                font.weight: Font.Bold
                                font.pixelSize: 26
                                width: list.width - arrow.width - direction.width
                                wrapMode: Text.WordWrap

                                Row {
                                    id: direction
                                    visible: model.coordinate.valid
                                    anchors.top: mainText.top
                                    anchors.left: mainText.right

                                    Label {
                                        text: (model.coordinate.valid) ? F.formatDistance(F.getDistanceTo(gps.lastGoodFix.lat, gps.lastGoodFix.lon, model.coordinate.lat, model.coordinate.lon), settings) : ""
                                        font.weight: Font.Light
                                        font.pixelSize: 26
                                        //width: implicitWidth
                                    }

                                    Image {
                                        id: arrowDirection
                                        source: "../data/small-arrow" + (theme.inverted ? "-night" : "") + ".png"
                                        transform: Rotation{
                                            angle: (model.coordinate.valid) ? (-compass.azimuth + F.getBearingTo(gps.lastGoodFix.lat, gps.lastGoodFix.lon, model.coordinate.lat, model.coordinate.lon)) : 0
                                            origin.x: arrowDirection.width/2
                                            origin.y: arrowDirection.height/2
                                        }
                                        visible: (gps.lastGoodFix.valid && model.coordinate.valid)
                                    }
                                }
                            }

                            Label {
                                id: subText
                                text: model.coordinate.comment
                                font.weight: Font.Light
                                font.pixelSize: 22
                                color: theme.inverted ? UI.COLOR_DESCRIPTION_NIGHT : UI.COLOR_DESCRIPTION
                                visible: text != ""
                                width: list.width - arrow.width
                                wrapMode: Text.WordWrap
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
                        id: arrow
                        source: "image://theme/icon-m-common-drilldown-arrow" + (theme.inverted ? "-inverse" : "")
                        anchors.right: parent.right;
                        anchors.verticalCenter: parent.verticalCenter
                    }

                    MouseArea {
                        id: mouseArea
                        anchors.fill: background
                        onClicked: {
                            //listPage.openFile(page)
                            showDescription.coordinate = model.coordinate
                            if (showDescription.coordinate.valid) {
                                map.setCenterLatLon(showDescription.coordinate.lat, showDescription.coordinate.lon)
                                map.visible = true;
                            } else {
                                map.visible = false;
                            }

                            showDescription.open()
                        }
                    }
                    height: r.height + 16
                    width: col1.width
                }

            }

            Label {
                font.pixelSize: 20
                color: UI.COLOR_INFOLABEL
                text: "Calculated Coordinates"
                visible: currentGeocache.calcCoordinates.length > 0
            }


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
                            anchors.verticalCenter: parent.verticalCenter
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
                            anchors.verticalCenter: parent.verticalCenter
                        }
                        height: labelText.height + 16
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
                                text: "From <b>" + model.coordinate.source + "</b>"
                                //font.weight: Font.Bold
                                font.pixelSize: 26
                                width: list.width - arrow.width - direction.width
                                wrapMode: Text.WordWrap

                                Row {
                                    id: direction
                                    visible: model.coordinate.result.valid
                                    anchors.top: mainText.top
                                    anchors.left: mainText.right

                                    Label {
                                        text: (model.coordinate.result.valid) ? F.formatDistance(F.getDistanceTo(gps.lastGoodFix.lat, gps.lastGoodFix.lon, model.coordinate.result.lat, model.coordinate.result.lon), settings) : ""
                                        font.weight: Font.Light
                                        font.pixelSize: 26
                                        //width: implicitWidth
                                    }

                                    Image {
                                        id: arrowDirection
                                        source: "../data/small-arrow" + (theme.inverted ? "-night" : "") + ".png"
                                        transform: Rotation{
                                            angle: (model.coordinate.result.valid) ? (-compass.azimuth + F.getBearingTo(gps.lastGoodFix.lat, gps.lastGoodFix.lon, model.coordinate.result.lat, model.coordinate.result.lon)) : 0
                                            origin.x: arrowDirection.width/2
                                            origin.y: arrowDirection.height/2
                                        }
                                        visible: (model.coordinate.result.valid)
                                    }
                                }
                            }

                            Label {
                                id: subText
                                text: model.coordinate.originalText + ((model.coordinate.calculation != "") ? ("\n= " + model.coordinate.calculation) : "")
                                font.weight: Font.Light
                                font.pixelSize: 22
                                color: theme.inverted ? UI.COLOR_DESCRIPTION_NIGHT : UI.COLOR_DESCRIPTION
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

                            Label {
                                id: subText2
                                text: model.coordinate.text
                                font.weight: Font.Light
                                font.pixelSize: 22
                                //color: theme.inverted ? UI.COLOR_DESCRIPTION_NIGHT : UI.COLOR_DESCRIPTION
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
                    width: col1.width
                }
            }

        }
    }

    QueryDialog {
        id: showDescription
        property variant coordinate: false
        anchors.centerIn: parent
        acceptButtonText: "Set as Target"
        rejectButtonText: "cancel"
        titleText: coordinate ? coordinate.name : "undefined"
        // todo: Gesamtwert berechnen
        content: [
            Column {
                spacing: 8
                Label {
                    text: showDescription.coordinate.valid ? F.formatCoordinate(showDescription.coordinate.lat, showDescription.coordinate.lon, settings) : "undefined"
                    width: showDescription.width
                    font.weight: Font.Light
                    color: UI.COLOR_DIALOG_TEXT
                    wrapMode: Text.WordWrap
                    font.pixelSize: UI.FONT_DEFAULT
                    visible: showDescription.coordinate.valid || false
                }/*
                Label {
                    text: showDescription.coordinate.display_text || "undefined"
                    width: showDescription.width
                    font.weight: Font.Light
                    wrapMode: Text.WordWrap
                    color: UI.COLOR_DIALOG_TEXT
                    font.pixelSize: UI.FONT_SMALL
                }*/
                Label {
                    text: showDescription.coordinate ? showDescription.coordinate.comment : "undefined"
                    width: showDescription.width
                    wrapMode: Text.WordWrap
                    color: UI.COLOR_DIALOG_TEXT
                    font.pixelSize: UI.FONT_SMALL
                }
                PinchMap {
                    id: map
                    zoomLevel: 15
                    width: showDescription.width
                    height: 300
                    clip: true
                    centerLatitude: showDescription.coordinate.lat || 49
                    centerLongitude: showDescription.coordinate.lon || 6
                    showTargetIndicator: true
                    showTargetAtLat: showDescription.coordinate.lat || 49
                    showTargetAtLon: showDescription.coordinate.lon || 6

                }
            }

        ]
        onAccepted: {
            controller.setAsTarget(coordinate)
            showMessage("New Target set.")
        }
    }
}
