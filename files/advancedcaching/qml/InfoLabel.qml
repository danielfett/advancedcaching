import QtQuick 1.1
import com.nokia.meego 1.0
import "uiconstants.js" as UI

Item {
    property int size: 0
    property alias name: title.text
    property alias value: value.text
    Text {
        id: title
        font.pixelSize: 20
        y: 0
        color: UI.COLOR_INFOLABEL
    }
    Text {
        id: value
        font.pixelSize: UI.FONT_DEFAULT
        y: 32
    }

    height: 40 + 26 // Defined by StarRating's height
    anchors.topMargin: 16
    width: 40*5 // Defined by StarRating's width
}
