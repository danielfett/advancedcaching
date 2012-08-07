import com.nokia.meego 1.0
import QtQuick 1.1
import "uiconstants.js" as UI
import "functions.js" as F

Column {

    function setValue(lat, lon) {
        console.log("Trying to set lat/lon to " + lat + " and " + lon);
        var v1 = F.getDM(lat)
        var v2 = F.getDM(lon)
        console.debug("v1="+v1+"  v2="+v2);
        latButton.value = v1[0]
        lat1.value = parseInt(v1[1][1])
        lat2.value = parseInt(v1[1][2])
        lat3.value = parseInt(v1[2][0])
        lat4.value = parseInt(v1[2][1])
        lat5.value = parseInt(v1[2][3])
        lat6.value = parseInt(v1[2][4])
        lat7.value = parseInt(v1[2][5])
        lonButton.value = v2[0]
        lon0.value = parseInt(v2[1][0])
        lon1.value = parseInt(v2[1][1])
        lon2.value = parseInt(v2[1][2])
        lon3.value = parseInt(v2[2][0])
        lon4.value = parseInt(v2[2][1])
        lon5.value = parseInt(v2[2][3])
        lon6.value = parseInt(v2[2][4])
        lon7.value = parseInt(v2[2][5])
    }

    function getValue() {
        var lat = F.getValueFromDM(latButton.value, 10 * lat1.value + lat2.value, 10*lat3.value + lat4.value + lat5.value/10 + lat6.value/100 + lat7.value/1000)
        var lon = F.getValueFromDM(lonButton.value, 100*lon0.value + 10 * lon1.value + lon2.value, 10*lon3.value + lon4.value + lon5.value/10 + lon6.value/100 + lon7.value/1000)
        return [lat, lon]
    }

    id: selectColumn
    spacing: 10
    // Latitude
    Button {
        id: latButton
        property int value: 1
        text: (latButton.value > 0) ? "N" : "S"
        font.pixelSize: UI.FONT_LARGE
        onClicked: { latButton.value = -latButton.value }
        width: UI.WIDTH_SELECTOR
    }
    Row {
        UpDownSelect {
            id: lat1
        }

        UpDownSelect {
            id: lat2
        }

        Label {
            text: "°"
            font.pixelSize:  UI.FONT_LARGE
            color: theme.inverted ? UI.COLOR_DIALOG_TEXT : UI.COLOR_DIALOG_TEXT_NIGHT
            anchors.verticalCenter: parent.verticalCenter
        }

        UpDownSelect {
            id: lat3
            max: 5
        }

        UpDownSelect {
            id: lat4
        }

        Label {
            text: "."
            font.pixelSize:  UI.FONT_LARGE
            anchors.verticalCenter: parent.verticalCenter
            color: theme.inverted ? UI.COLOR_DIALOG_TEXT : UI.COLOR_DIALOG_TEXT_NIGHT
        }

        UpDownSelect {
            id: lat5
        }

        UpDownSelect {
            id: lat6
        }

        UpDownSelect {
            id: lat7
        }
    }
    // Longitude
    Button {
        id: lonButton
        property int value: 1
        text: (lonButton.value > 0) ? "E" : "W"
        font.pixelSize: UI.FONT_LARGE
        onClicked: { lonButton.value = -lonButton.value }
        width: UI.WIDTH_SELECTOR
    }
    Row {

        UpDownSelect {
            id: lon0
            max: 1
        }

        UpDownSelect {
            id: lon1
        }

        UpDownSelect {
            id: lon2
        }
        Label {
            text: "°"
            font.pixelSize:  UI.FONT_LARGE
            anchors.verticalCenter: parent.verticalCenter
            color: theme.inverted ? UI.COLOR_DIALOG_TEXT : UI.COLOR_DIALOG_TEXT_NIGHT
        }

        UpDownSelect {
            id: lon3
            max: 5
        }

        UpDownSelect {
            id: lon4
        }

        Label {
            text: "."
            font.pixelSize:  UI.FONT_LARGE
            anchors.verticalCenter: parent.verticalCenter
            color: theme.inverted ? UI.COLOR_DIALOG_TEXT : UI.COLOR_DIALOG_TEXT_NIGHT
        }

        UpDownSelect {
            id: lon5
        }

        UpDownSelect {
            id: lon6
        }

        UpDownSelect {
            id: lon7
        }
    }

}
