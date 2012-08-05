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
                width: 400
                font.weight: Font.Light
                wrapMode: Text.WordWrap
                font.pixelSize: UI.FONT_DEFAULT
                visible: (showDescription.coordinate && showDescription.coordinate.valid) || false
            }
            Label {
                text: coordinate ? coordinate.comment : "undefined"
                width: 400
                wrapMode: Text.WordWrap
                font.pixelSize: UI.FONT_SMALL
            }
            PinchMap {
                id: map
                zoomLevel: 15
                width: 400
                height: 300
                clip: true
                showTargetIndicator: true
                showTargetAtLat: coordinate.lat || 0
                showTargetAtLon: coordinate.lon || 0
                visible: false
                status: showDescription.status
                url: settings.currentMapType.url
            }
        }

    ]
    onAccepted: {
        controller.setAsTarget(coordinate)
        showMessage("New Target set.")
    }
}
