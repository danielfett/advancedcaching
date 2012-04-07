import com.nokia.meego 1.0
import QtQuick 1.1

Sheet {
    id: test
    //anchors.centerIn: parent
    acceptButtonText: "Save"
    rejectButtonText: "Close"
    //titleText: "Edit Coordinate"

    function getValue() {
        return cs.getValue();
    }

    function setValue(lat, lon) {
        cs.setValue(lat,lon);
    }

    content: [
        MouseArea { // to keep the dialog from closing when the user clicks on the background
            anchors.fill: cs
            onClicked: {  }
        },
        CoordinateSelector {
            id: cs
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.top
            anchors.topMargin: 16
        }

    ]
}
