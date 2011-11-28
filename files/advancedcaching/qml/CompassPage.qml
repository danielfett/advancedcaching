import QtQuick 1.1
import com.nokia.meego 1.0
import "uiconstants.js" as UI

Page {
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
                    id: azCompass
                    origin.x: compassImage.width/2
                    origin.y: compassImage.height/2
                    angle: -compass.azimuth
                }/*,
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
                property int outerMargin: 15
                id: sunImage
                source: "image://theme/icon-m-weather-sunny"
                x: compassImage.width/2 - width/2
                y: sunImage.outerMargin
                z: -1
                transform: Rotation {
                   origin.y: compassImage.height/2 - sunImage.outerMargin
                   origin.x: sunImage.width/2
                   angle: sunImage.angle
               }
            }
            Image {
                property int angle: gps.targetBearing
                property int outerMargin: 50
                id: arrowImage
                source: "../data/arrow_target.svg"
                width: (compassImage.paintedWidth / compassImage.sourceSize.width)*sourceSize.width
                fillMode: Image.PreserveAspectFit
                x: compassImage.width/2 - width/2
                y: arrowImage.outerMargin
                z: 3
                transform: Rotation {
                   origin.y: compassImage.height/2 - arrowImage.outerMargin
                   origin.x: arrowImage.width/2
                   angle: arrowImage.angle
               }
            }
        }


        Row {
            InfoLabel {
                name: "Travel Direction"
                value: gps.lastGoodFix.bearing + "°"
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

        Row {
            InfoLabel {
                name: "Distance"
                value: gps.targetDistance + " m"
                width: compassColumn.width/3.0
            }
            InfoLabel {
                name: "Accuracy"
                value: "± " + gps.lastGoodFix.error + " m"
                width: compassColumn.width/3.0
            }
            InfoLabel {
                name: "Altitude"
                value: gps.lastGoodFix.altitude + " m"
                width: compassColumn.width/3.0
            }
        }

        InfoLabel {
            name: "Current Position"
            value: gps.lastGoodFix.lat + "-" + gps.lastGoodFix.lon//"N49° 44.123 E6° 23.541"
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
                onClicked: {
                    //coordinateSelectorDialog.parent = tabCompass
                    coordinateSelectorDialog.open()
                }
            }
        }

    }
}
