import QtQuick 1.1
import com.nokia.meego 1.0
import "uiconstants.js" as UI

Column {
    property int max: 9
    property int value: 0
    Button {
        iconSource: "image://theme/icon-s-common-add"
        width: UI.WIDTH_SELECTOR
        onClicked: { value = (value + 1) % (max + 1) }
    }
    Label {
        id: valueText
        font.pixelSize: UI.FONT_LARGE
        text: value
        anchors.horizontalCenter: parent.horizontalCenter
        color: "white"
    }
    Button {
        iconSource: "image://theme/icon-s-common-remove"
        width: UI.WIDTH_SELECTOR
        onClicked: { value = (value > 0) ? (value - 1) : max }
    }

    width: UI.WIDTH_SELECTOR
}

