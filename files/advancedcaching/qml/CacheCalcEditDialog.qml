import QtQuick 1.1
import com.nokia.meego 1.0
import "uiconstants.js" as UI
import "functions.js" as F

Sheet {
    id: editCalc
    property variant coordinate: null
    property variant manager: null
    property variant buttonText: ""
    property bool isCoordinate: false
    property bool isKnown: false
    //anchors.centerIn: parent
    acceptButtonText: view.checked ? ((isCoordinate || (coordinate ? coordinate.hasRequires : false)) ? "Set as Target" : "") : "Save"
    rejectButtonText: "Close"
    //titleText: "CacheCalc"

    function editCalcCoordinate(geocache, c) {
        coordinate = c;
        manager = controller.getEditWrapper(geocache, c);
        edit.checked = true;
    }

    function editCalcCoordinateByID(geocache, id) {
        coordinate = null;
        manager = controller.getEditWrapperByID(geocache, id);
        edit.checked = true;
    }

    function addCalc(geocache) {
        coordinate = null;
        manager = controller.getAddCalcWrapper(geocache);
        edit.checked = true;
    }

    function addCoordinate(geocache) {
        coordinate = null;
        manager = controller.getAddCoordinateWrapper(geocache);
        edit.checked = true;
    }

    onManagerChanged: {
        textName.text = manager.beforeName
        buttonText = manager.buttonText
        isCoordinate = manager.isCoordinate
        if (isCoordinate) {
            cs.setValue(manager.beforeCoordinate.lat, manager.beforeCoordinate.lon);
            warning.text = '';
            coordinate = manager.beforeCoordinate
            isKnown = true;
            map.setCenterLatLon(coordinate.lat, coordinate.lon);
            map.showTargetIndicator = true;
            map.showTargetAtLat = coordinate.lat;
            map.showTargetAtLon = coordinate.lon;
        } else {
            textCalc.text = manager.beforeCalc
            // 2 == USER_TYPE_CALC_STRING_OVERRIDE
            warning.text = (manager.ctype == 2) ? "If you make changes here, this will replace the calculation which was found in the listing." : ""
            isKnown = (coordinate != null && coordinate.hasRequires);
            if (isKnown) {
                map.setCenterLatLon(coordinate.result.lat, coordinate.result.lon);
                map.showTargetIndicator = true;
                map.showTargetAtLat = coordinate.result.lat;
                map.showTargetAtLon = coordinate.result.lon;
            } else {
                map.showTargetIndicator = false;
            }
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
            spacing: 16

            states: [State{
                    name: "VIEW-CALC-UNKNOWN"
                    PropertyChanges { target: unknown; visible: true; }
                    PropertyChanges { target: coordinates; visible: false; }
                    PropertyChanges { target: map; visible: false; }
                    PropertyChanges { target: colView; visible: true; }
                    PropertyChanges { target: colEdit; visible: false; }
                    when: (! isCoordinate && ! isKnown && view.checked)
                },
                State {
                    name: "VIEW-CALC-KNOWN"
                    PropertyChanges { target: unknown; visible: false; }
                    PropertyChanges { target: coordinates; visible: true; }
                    PropertyChanges { target: map; visible: true; }
                    PropertyChanges { target: colView; visible: true; }
                    PropertyChanges { target: colEdit; visible: false; }
                    when: (! isCoordinate && isKnown && view.checked)
                },
                State {
                    name: "VIEW-COORDINATE"
                    PropertyChanges { target: unknown; visible: false; }
                    PropertyChanges { target: coordinates; visible: true; }
                    PropertyChanges { target: map; visible: true; }
                    PropertyChanges { target: colView; visible: true; }
                    PropertyChanges { target: colEdit; visible: false; }
                    when: (isCoordinate && view.checked)
                },
                State {
                    name: "EDIT-CALC"
                    PropertyChanges { target: map; visible: false; }
                    PropertyChanges { target: labelCalc; visible: true; }
                    PropertyChanges { target: textCalc; visible: true; }
                    PropertyChanges { target: colView; visible: false; }
                    PropertyChanges { target: colEdit; visible: true; }
                    PropertyChanges { target: cs; visible: false; }
                    when: (!isCoordinate && edit.checked)
                },
                State {
                    name: "EDIT-COORDINATE"
                    PropertyChanges { target: map; visible: false; }
                    PropertyChanges { target: labelCalc; visible: false; }
                    PropertyChanges { target: textCalc; visible: false; }
                    PropertyChanges { target: colView; visible: false; }
                    PropertyChanges { target: colEdit; visible: true; }
                    PropertyChanges { target: cs; visible: true; }
                    when: (isCoordinate && edit.checked)
                }

            ]

            onStateChanged: {
                console.debug("STATE is now " + state);
                if (state == 'VIEW-COORDINATE') {
                    var c = cs.getValue();
                    map.setCenterLatLon(c[0], c[1]);
                    map.showTargetIndicator = true;
                    map.showTargetAtLat = c[0];
                    map.showTargetAtLon = c[1];
                }
            }

            ButtonRow {
                Button { id: view; text: "View"; onClicked: { } }
                Button { id: edit; text: "Edit"; onClicked: { } }
            }

            Column {
                id: colView
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: 8



                // VIEW
                Label {
                    id: unknown
                    text: "?"
                    font.pixelSize: 200
                    color: "#444444"
                    anchors.horizontalCenter: parent.horizontalCenter
                }

                Label {
                    id: coordinates
                    text: (coordinate && coordinate.hasRequires) ? F.formatCoordinate(coordinate.result.lat, coordinate.result.lon, settings) : "undefined"
                    width: 400
                    font.weight: Font.Light
                    color: UI.COLOR_DIALOG_TEXT
                    wrapMode: Text.WordWrap
                    font.pixelSize: UI.FONT_DEFAULT
                    anchors.horizontalCenter: parent.horizontalCenter
                }
                PinchMap {
                    id: map
                    zoomLevel: 15
                    width: 400//showDescription.width
                    height: 300
                    clip: true
                    anchors.horizontalCenter: parent.horizontalCenter
                }

            }

            Column {
                id: colEdit
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: 8

                Label {
                    id: warning
                    font.pixelSize: 20
                    color: theme.inverted ? UI.COLOR_WARNING_NIGHT : UI.COLOR_WARNING_DARKBG
                    text: ""
                    width: 400
                    wrapMode: Text.Wrap
                }

                Label {
                    id: labelName
                    font.pixelSize: 20
                    color: UI.COLOR_INFOLABEL
                    text: "Name"
                    width: 400
                    wrapMode: Text.Wrap
                }
                TextField {
                    id: textName
                    placeholderText: "Name"
                    width: 400
                    visible: edit.checked
                }

                Label {
                    id: labelCalc
                    font.pixelSize: 20
                    color: UI.COLOR_INFOLABEL
                    text: "Coordinate or Calc String. You can use A-Z and the operators () +-*/.\nExample: N34 AB.CDE E3 (A+B*2)C.DE(B-9)"
                    width: 400
                    wrapMode: Text.Wrap
                }

                TextField {
                    id: textCalc
                    placeholderText: "N12 34.567 W12 34.567"
                    width: 400
                }

                CoordinateSelector {
                    id: cs
                }

                Button {
                    id: deleteButton
                    text: buttonText
                    onClicked: {
                        manager.deleteCalc();
                        editCalc.close();
                    }
                    anchors.horizontalCenter: parent.horizontalCenter
                    visible: text != ""
                }
            }

        }



    ]
    onAccepted: {
        if (edit.checked) {
            save();
        } else if (isCoordinate) {
            controller.setAsTarget(coordinate)
            showMessage("New Target set.")
        } else if (coordinate.hasRequires) {
            controller.setAsTarget(coordinate.result)
            showMessage("New Target set.")
        }
    }

    function save() {
        if (isCoordinate) {
            var v = cs.getValue();
            showMessage(manager.saveCoordinate(textName.text, v[0], v[1]));
            return;
        }

        if (textName.text != manager.beforeName || textCalc.text != manager.beforeCalc) {
            showMessage(manager.save(textName.text, textCalc.text));
            return;
        }
    }
}
