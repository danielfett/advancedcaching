import QtQuick 1.1
import com.nokia.meego 1.0
import "uiconstants.js" as UI
import "functions.js" as F

QueryDialog {
    id: editCalc
    property variant coordinate: null
    property variant manager: null
    property variant buttonText: ""
    anchors.centerIn: parent
    acceptButtonText: view.checked ? (coordinate.hasRequires ? "Set as Target" : "") : "Save"
    rejectButtonText: ""
    titleText: "CacheCalc"

    onCoordinateChanged: {
        manager = controller.getEditWrapper(currentGeocache, coordinate);
    }

    onManagerChanged: {
        textName.text = manager.beforeName
        textCalc.text = manager.beforeCalc
        buttonText = manager.buttonText
        // 2 == USER_TYPE_CALC_STRING_OVERRIDE
        warning.text = (manager.ctype == 2) ? "If you make changes here, this will replace the calculation which was found in the listing." : ""
    }

    content: [
        Column {
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 8
            ButtonRow {
                Button { id: view; text: "View"; onClicked: { } }
                Button { id: edit; text: "Edit"; onClicked: { } }
            }

            // VIEW
            Label {
                text: "?"
                font.pixelSize: 200
                color: "#444444"
                visible: (view.checked && ! coordinate.hasRequires)
                anchors.horizontalCenter: parent.horizontalCenter
            }

            Label {
                text: coordinate.hasRequires ? F.formatCoordinate(coordinate.result.lat, coordinate.result.lon, settings) : "undefined"
                width: 400//showDescription.width
                font.weight: Font.Light
                color: UI.COLOR_DIALOG_TEXT
                wrapMode: Text.WordWrap
                font.pixelSize: UI.FONT_DEFAULT
                visible: (coordinate.hasRequires && view.checked) || false
                anchors.horizontalCenter: parent.horizontalCenter
            }
            PinchMap {
                id: map
                zoomLevel: 15
                width: 400//showDescription.width
                height: 300
                clip: true
                centerLatitude: coordinate.hasRequires ? coordinate.result.lat : 0 || 0
                centerLongitude: coordinate.hasRequires ? coordinate.result.lon : 0 || 0
                showTargetIndicator: true
                showTargetAtLat: coordinate.hasRequires ? coordinate.result.lat : 0 || 0
                showTargetAtLon: coordinate.hasRequires ? coordinate.result.lon : 0 || 0
                visible: (coordinate.hasRequires && view.checked) || false
                anchors.horizontalCenter: parent.horizontalCenter
            }

            // EDIT


            Label {
                id: warning
                font.pixelSize: 20
                color: theme.inverted ? UI.COLOR_WARNING_NIGHT : UI.COLOR_WARNING_DARKBG
                text: ""
                width: 400
                visible: (text != "" && edit.checked)
                wrapMode: Text.Wrap
            }

            Label {
                font.pixelSize: 20
                color: UI.COLOR_INFOLABEL
                text: "Name"
                width: 400
                visible: edit.checked
                wrapMode: Text.Wrap
            }
            TextField {
                id: textName
                placeholderText: "Name"
                width: 400
                visible: edit.checked
            }

            Label {
                font.pixelSize: 20
                color: UI.COLOR_INFOLABEL
                text: "Coordinate or Calc String. You can use A-Z and the operators () +-*/.\nExample: N34 AB.CDE E3 (A+B*2)C.DE(B-9)"
                width: 400
                visible: edit.checked
                wrapMode: Text.Wrap
            }

            TextField {
                id: textCalc
                placeholderText: "N12 34.567 W12 34.567"
                width: 400
                visible: edit.checked
            }

            Button {
                text: buttonText
                visible: (text != "" && edit.checked)
                onClicked: {
                    manager.deleteCalc();
                    editCalc.close();
                }
                anchors.horizontalCenter: parent.horizontalCenter
            }
        }

    ]
    onAccepted: {
        if (edit.checked) {
            save();
        } else if (coordinate.hasRequires) {
            controller.setAsTarget(coordinate.result)
            showMessage("New Target set.")
        }
    }

    function save() {
        if (textName.text != manager.beforeName || textCalc.text != manager.beforeCalc) {
            showMessage(manager.save(textName.text, textCalc.text));
        }
    }
}
