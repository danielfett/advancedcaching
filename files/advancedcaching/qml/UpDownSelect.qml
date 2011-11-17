import QtQuick 1.1
import com.nokia.meego 1.0
import "uiconstants.js" as UI

Column {
    property alias num: value.text
    property int max: 9
    Button {
        iconSource: "image://theme/icon-s-common-add"
        width: UI.WIDTH_SELECTOR
    }
    Text {
        id: value
        font.pixelSize: UI.FONT_LARGE
        text: "2"
        anchors.horizontalCenter: parent.horizontalCenter
    }
    Button {
        iconSource: "image://theme/icon-s-common-remove"
        width: UI.WIDTH_SELECTOR
    }

    width: UI.WIDTH_SELECTOR
}

