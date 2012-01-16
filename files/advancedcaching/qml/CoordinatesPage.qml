import QtQuick 1.1
import com.nokia.meego 1.0
import "uiconstants.js" as UI
import "functions.js" as F

Page {
    id: listPage
    orientationLock: PageOrientation.LockPortrait
    tools: commonTools
    GeocacheHeader{
        cache: currentGeocache
        id: listHeader
    }

    onStatusChanged: {
        if (status == PageStatus.Inactive && tabDetailsPageStack.depth == 1) {
            pageCoordinates.source = "";
        }
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
                text: "Coordinates from the Listing"
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
                            if (model.coordinate.userCoordinateID == -1) {
                                showDescription.source = "CoordinateDetailsDialog.qml"
                                showDescription.item.coordinate = model.coordinate
                                showDescription.item.open()
                            } else {
                                editCalc.source = "CacheCalcEditDialog.qml";
                                editCalc.item.editCalcCoordinateByID(currentGeocache, model.coordinate.userCoordinateID);
                                editCalc.item.open();
                            }
                        }
                    }
                    height: r.height + 16
                    width: col1.width
                }

            }

            Label {
                font.pixelSize: 20
                color: UI.COLOR_INFOLABEL
                text: "Found and Calculated Coordinates"
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
                            property bool init: false
                            placeholderText: "?"
                            width: 90
                            id: labelText
                            text: "" + model.vars.value
                            font.pixelSize: 28
                            onTextChanged: {
                                if (init || model.vars.value == "") {
                                    model.vars.value = text
                                }
                                init = true;
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
                                color: theme.inverted ? UI.COLOR_WARNING_NIGHT : UI.COLOR_WARNING
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
                            editCalc.source = "CacheCalcEditDialog.qml";
                            editCalc.item.editCalcCoordinate(currentGeocache, model.coordinate);
                            editCalc.item.open();
                        }
                    }
                    height: r.height + 16
                    width: col1.width
                }
            }

        }
    }

    Loader {
        id: showDescription
    }

    Loader {
        id: editCalc
    }

    function openMenu() {
        menu.open();
    }



    Menu {
        id: menu
        visualParent: parent

        MenuLayout {
            MenuItem { text: "Add Calc string"; onClicked: {
                    editCalc.source = "CacheCalcEditDialog.qml";
                    editCalc.item.addCalc(currentGeocache);
                    editCalc.item.open();
                } }

            MenuItem { text: "Add coordinate"; onClicked: {
                    editCalc.source = "CacheCalcEditDialog.qml";
                    editCalc.item.addCoordinate(currentGeocache);
                    editCalc.item.open();
                } }
            MenuItem { text: "Settings"; onClicked: { showSettings(); } }
        }
    }
}
