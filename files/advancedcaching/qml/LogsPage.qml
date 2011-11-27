import QtQuick 1.1
import com.nokia.meego 1.0
import "uiconstants.js" as UI

Page {
    
    Header{
        text: "Geocache <b>GCEZ71U</b>"
        id: listHeader
    }

    ListModel {
        id: listModel
        ListElement {
            user: "webhamster"
            date: "2011-10-31"
            description: "Leicht gefundenes Fressen. Lorem ipsum Dolor sit amet, in consectuum consequat. Toller Geocache, gerne wieder, schnell verschickt.<br><br>TFTC!"
        }
    }

    ListView {
        anchors.top: listHeader.bottom
        anchors.leftMargin: 16
        anchors.rightMargin: 16
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom:  parent.bottom
        model: listModel
        delegate: Column {
            height: rw.height + description.height + 16
            spacing: 16
            Row {
                id: rw
                spacing: 16
                Image {
                    source: "../data/wrench.png"
                    id: icon
                    anchors.top: logTitle.top
                }

                Text {
                    text: "<b>Found by " + model.user + "<br>on " + model.date + "</b>"
                    font.weight: Font.Bold
                    font.pixelSize: UI.FONT_SMALL
                    id: logTitle
                }
            }

            Text {
                id: description
                font.weight: Font.Light
                text: model.description
                wrapMode: Text.Wrap
                font.pixelSize: UI.FONT_SMALL
                color: UI.COLOR_DESCRIPTION
                width: parent.parent.width - 2*16
            }
        }
    }

}
