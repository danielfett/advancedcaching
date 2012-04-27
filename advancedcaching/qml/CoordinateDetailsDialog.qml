import QtQuick 1.1
import com.nokia.meego 1.0
import "uiconstants.js" as UI
import "functions.js" as F

Sheet {
    id: showDescription
    property variant coordinate: null
    acceptButtonText: "Set as Target"
    rejectButtonText: "Close"
    //titleText: coordinate ? coordinate.name : "undefined"

    onCoordinateChanged: {
        if (coordinate && coordinate.valid) {
            map.visible = true;
            map.setCenterLatLon(coordinate.lat, coordinate.lon);
        } else {
            map.visible = false;
        }
    }

    content: [
        MouseArea {
            anchors.fill: parent
            onClicked: { } // to prevent "clicking through" the dialog background
        },
        Column {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.top
            anchors.topMargin: 16
            spacing: 8
            Label {
                text: coordinate.valid ? F.formatCoordinate(coordinate.lat, coordinate.lon, settings) : "undefined"
                width: 400//showDescription.width
                font.weight: Font.Light
                color: UI.COLOR_DIALOG_TEXT
                wrapMode: Text.WordWrap
                font.pixelSize: UI.FONT_DEFAULT
                visible: showDescription.coordinate && showDescription.coordinate.valid
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
                text: coordinate ? coordinate.comment : "undefined"
                width: 400//showDescription.width
                wrapMode: Text.WordWrap
                color: UI.COLOR_DIALOG_TEXT
                font.pixelSize: UI.FONT_SMALL
            }
            PinchMap {
                id: map
                zoomLevel: 15
                width: 400//showDescription.width
                height: 300
                clip: true
                showTargetIndicator: true
                showTargetAtLat: coordinate.lat || 0
                showTargetAtLon: coordinate.lon || 0
                visible: false
            }
        }

    ]
    onAccepted: {
        controller.setAsTarget(coordinate)
        showMessage("New Target set.")
    }
}
