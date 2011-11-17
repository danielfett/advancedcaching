import QtQuick 1.1
import com.nokia.meego 1.0

Column {
    property alias num: value.text
    Button {
        text: "+"
    }
    Text {
        id: value
        font.pixelSize: UI.FONT_LARGE
        text: "2"
    }
    Button {
        text: "-"
    }
}

