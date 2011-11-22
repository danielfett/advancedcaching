import QtQuick 1.1
import com.nokia.meego 1.0
import "uiconstants.js" as UI

Page {
    
    Header{
        text: "Geocache <b>GCEZ71U</b>"
        id: header
    }
    
    Image {
        source: "../data/wrench.png"
        x: 16
        anchors.top: header.bottom
        anchors.topMargin: 16
        id: icon
    }
    
    Text { 
        text: "<b>Found by webhamster<br>on 2011-10-31</b>"
        anchors.left: icon.right
        anchors.leftMargin: 16
        font.pixelSize: UI.FONT_SMALL
        id: logTitle
        anchors.top: icon.top
    }
    
    Text {
        text: "Leicht gefundenes Fressen. Lorem ipsum Dolor sit amet, in consectuum consequat. Toller Geocache, gerne wieder, schnell verschickt.<br><br>TFTC!"
        wrapMode: Text.Wrap
        anchors.left: parent.left
        anchors.top: logTitle.bottom
        anchors.leftMargin: 16
        anchors.rightMargin: 16
        anchors.topMargin: 16
        anchors.right: parent.right
        font.pixelSize: UI.FONT_SMALL
    }
}
