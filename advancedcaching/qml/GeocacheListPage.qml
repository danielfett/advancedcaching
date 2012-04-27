import QtQuick 1.1
import com.nokia.meego 1.0
import "uiconstants.js" as UI
import "functions.js" as F

Page {
    id: listPage
    orientationLock: PageOrientation.LockPortrait

    property alias model: list.model

    onStatusChanged: {
        if (status == PageStatus.Inactive && tabListPageStack.depth == 1) {
            console.debug("Unloaded!");
            pageGeocacheList.source = "";
        }
    }

    property alias title: header.text

    Header{
        text: "List Geocaches"
        id: header
    }

    ListView {
        anchors.top: header.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom:  parent.bottom
        clip: true

        cacheBuffer: 500
        model: emptyList
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
                spacing: 8

                Rectangle {
                    color: UI.getCacheColor(model.geocache)
                    width: 20
                    height: 20
                    radius: 6
                }

                Column {

                    Label {
                        id: mainText
                        text: model.geocache.title || "No Title"
                        font.weight: Font.Bold
                        font.pixelSize: 26
                        width: list.width - arrow.width - direction.width - 16 - 20
                        wrapMode: Text.WordWrap

                        Row {
                            id: direction
                            anchors.top: mainText.top
                            anchors.left: mainText.right

                            Label {
                                text: F.formatDistance(F.getDistanceTo(gps.lastGoodFix.lat, gps.lastGoodFix.lon, model.geocache.lat, model.geocache.lon), settings)
                                font.weight: Font.Light
                                font.pixelSize: 26
                                //width: implicitWidth
                            }

                            Image {
                                id: arrowDirection
                                source: "../data/small-arrow" + (theme.inverted ? "-night" : "") + ".png"
                                transform: Rotation{
                                    angle: -compass.azimuth + F.getBearingTo(gps.lastGoodFix.lat, gps.lastGoodFix.lon, model.geocache.lat, model.geocache.lon)
                                    origin.x: arrowDirection.width/2
                                    origin.y: arrowDirection.height/2
                                }
                                visible: gps.lastGoodFix.valid
                            }
                        }
                    }

                    Label {
                        id: subText
                        text: model.geocache.strippedShortdesc
                        font.weight: Font.Light
                        font.pixelSize: 22
                        color: theme.inverted ? UI.COLOR_DESCRIPTION_NIGHT : UI.COLOR_DESCRIPTION
                        visible: text != ""
                        width: list.width - arrow.width - 16 - 20
                        wrapMode: Text.WordWrap
                    }

                    Label {
                        id: subCoordinate
                        text: model.geocache.name + " - " + (model.geocache.type == "regular" ? "traditional" : model.geocache.type)
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
                    showAndResetDetailsPage()
                    controller.geocacheSelected(model.geocache)
                }
            }
            height: r.height + 16
            width: parent.width
        }

    }


    function openMenu() {
        console.debug("Opening Menu!")
        menu.open();
    }

    Menu {
        id: menu
        visualParent: parent

        MenuLayout {

            MenuItem { text: "Add all to favorites"; onClicked: {
                    model.markAll(true);
                } }

            MenuItem { text: "Remove all from favorites"; onClicked: {
                    model.markAll(false);
                } }
                
            MenuItem { text: "Download Details for all"; onClicked: {
                    model.downloadDetails();
                } }

            MenuItem { text: "Sort by Name"; onClicked: {
                    model.sort(1, null);
                } }

            MenuItem { text: "Sort by Proximity"; onClicked: {
                    model.sort(0, gps);
                } }

            MenuItem { text: "Sort by Type, Found"; onClicked: {
                    model.sort(2, null);
                } }

            MenuItem { text: "Sort by Found, Type"; onClicked: {
                    model.sort(3, null);
                } }
            MenuItem { text: "Settings"; onClicked: { showSettings(); } }
        }
    }
}
