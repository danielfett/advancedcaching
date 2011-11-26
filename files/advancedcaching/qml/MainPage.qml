import QtQuick 1.1
import com.nokia.meego 1.0
import "uiconstants.js" as UI
import QtWebKit 1.0


Page {
    id: listPage
    //anchors.margins: rootWindow.pageMargin
    tools: commonTools
    TabGroup {
        id: tabGroup
        currentTab: tabMap
        Page {
            id: tabCompass
            orientationLock: PageOrientation.LockPortrait

            Column {
                spacing: 10
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.verticalCenter: parent.verticalCenter
                anchors.fill: parent
                anchors.topMargin: 16
                anchors.leftMargin: 16
                anchors.rightMargin: 16
                id: compassColumn

                Image {
                    id: compassImage
                    source: "../data/windrose.svg"
                    transform: [Rotation {
                            origin.x: compassImage.width/2
                            origin.y: compassImage.height/2
                            angle: -compass.azimuth
                        },/*
                        Rotation {
                            origin.x: compassImage.width/2
                            origin.y: compassImage.height/2
                            axis {x: 0; y: 0; z: 1}
                            angle: accelerometer.x
                        }
                        ,
                        Rotation {
                            origin.x: compassImage.width/2
                            origin.y: compassImage.height/2
                            axis {x: 0; y: 1; z: 0}
                            angle: -accelerometer.x
                        },
                        Rotation {
                            origin.x: compassImage.width/2
                            origin.y: compassImage.height/2
                            axis {x: 1; y: 0; z: 0}
                            angle: -accelerometer.y
                        }*/]
                    //anchors.fill: parent
                    anchors.horizontalCenter: parent.horizontalCenter
                    smooth: true
                    width: compassColumn.width * 0.9
                    fillMode: Image.PreserveAspectFit
                    z: 2

                    Image {
                        property int angle: 90
                        property int radius: (compassImage.width/2) - 20
                        id: sunImage
                        source: "image://theme/icon-m-weather-sunny"
                        x: compassImage.x + compassImage.paintedWidth/2 - sunImage.width + radius*Math.sin((angle * Math.PI)/180)
                        y: -compassImage.y + compassImage.paintedHeight/2 - sunImage.width/2 + radius*Math.cos((angle * Math.PI)/180)
                        z: 1
                    }
                    Image {
                        property int angle: 90
                        id: arrowImage
                        source: "../data/arrow_target.svg"
                        width: (compassImage.paintedWidth / compassImage.sourceSize.width)*sourceSize.width
                        fillMode: Image.PreserveAspectFit
                        x: compassImage.width/2 - width/2
                        y: 50
                        z: 3
                        transform: Rotation {
                           origin.y: compassImage.height/2 - 50
                           origin.x: arrowImage.width/2
                           angle: arrowImage.angle
                       }
                    }
                }


                Row {
                    InfoLabel {
                        name: "Distance"
                        value: "256 m"
                        width: compassColumn.width/3.0
                    }
                    InfoLabel {
                        name: "Accuracy"
                        value: "± 5 m"
                        width: compassColumn.width/3.0
                    }
                    InfoLabel {
                        name: "Altitude"
                        value: "190 m"
                        width: compassColumn.width/3.0
                    }
                }
                Row {
                    InfoLabel {
                        name: "Travel Direction"
                        value: "43°"
                        width: compassColumn.width/3
                    }
                    InfoLabel {
                        name: "Comp. Heading"
                        value: compass.azimuth + "°"
                        width: compassColumn.width/3
                    }
                    InfoLabel {
                        name: "Comp. Accuracy"
                        value: (compass.calibration * 100) + "%"
                        width: compassColumn.width/3
                    }
                }

                InfoLabel {
                    name: "Current Position"
                    value: "N49° 44.123 E6° 23.541"
                    width: compassColumn.width
                }

                Row {
                    InfoLabel {
                        id: currentTarget
                        name: "Current Target"
                        value: "N119° 44.123 E6° 23.541"
                        width: compassColumn.width - changeTargetButton.width
                    }
                    Button {
                        id: changeTargetButton
                        width: compassColumn.width/5
                        anchors.bottom: currentTarget.bottom
                        iconSource: "image://theme/icon-m-toolbar-edit"
                    }
                }

            }
        }
        Page {
            id: tabMap
            PinchMap {
                id: pinchmap
                anchors.fill: parent
                //mapType: Map.StreetMap
            }
            Button {
                text: "test"
                onClicked: {pinchmap.setCenterLatLon(48.85568,2.386093) }
            }
            Rectangle {
                width: 10; height: 10; border.width: 1; border.color: "#ff0000";
                anchors.centerIn: pinchmap
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
            Button {
                text: "open"
                onClicked: {
                    var component = Qt.createComponent("CoordinateSelector.qml")
                    if (component.status == Component.Ready) {
                        var dialog = component.createObject(tabSettings)
                        dialog.open()
                    }
                    else
                        console.log("Error loading component:", component.errorString());
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
    /*

    */
    /*
     function openFile(file) {
         var component = Qt.createComponent(file)
         if (component.status == Component.Ready)
             pageStack.push(component);
         else
             console.log("Error loading component:", component.errorString());
     }

     ListModel {
         id: pagesModel
         ListElement {
             page: "SimpleExamplesPage.qml"
             title: "Simple examples"
             subtitle: "Buttons, TextField, ToolBar and ViewMenu"
         }
         ListElement {
             page: "DialogsPage.qml"
             title: "Dialogs"
             subtitle: "How to use different dialogs"
         }
     }

     ListView {
         id: listView
         anchors.fill: parent
         model: pagesModel

         delegate:  Item {
             id: listItem
             height: 88
             width: parent.width

             BorderImage {
                 id: background
                 anchors.fill: parent
                 // Fill page borders
                 anchors.leftMargin: -listPage.anchors.leftMargin
                 anchors.rightMargin: -listPage.anchors.rightMargin
                 visible: mouseArea.pressed
                 source: "image://theme/meegotouch-list-background-pressed-center"
             }

             Row {
                 anchors.fill: parent

                 Column {
                     anchors.verticalCenter: parent.verticalCenter

                     Label {
                         id: mainText
                         text: model.title
                         font.weight: Font.Bold
                         font.pixelSize: 26
                     }

                     Label {
                         id: subText
                         text: model.subtitle
                         font.weight: Font.Light
                         font.pixelSize: 22
                         color: "#cc6633"

                         visible: text != ""
                     }
                 }
             }

             Image {
                 source: "image://theme/icon-m-common-drilldown-arrow" + (theme.inverted ? "-inverse" : "")
                 anchors.right: parent.right;
                 anchors.verticalCenter: parent.verticalCenter
             }

             MouseArea {
                 id: mouseArea
                 anchors.fill: background
                 onClicked: {
                     listPage.openFile(page)
                 }
             }
         }
     }
     ScrollDecorator {
         flickableItem: listView
     }*/
}
