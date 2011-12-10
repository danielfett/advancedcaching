import QtQuick 1.0
import com.nokia.meego 1.0
import "uiconstants.js" as UI
import QtWebKit 1.0

Page {

    Flickable {
        anchors.fill: parent
        id: flick
        boundsBehavior: Flickable.DragOverBounds
        
        GeocacheHeader{
            cache: currentGeocache
            id: header
        }
        
        Column {
            id: col1
            spacing: 16
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.leftMargin: 16
            anchors.rightMargin: 16
            anchors.top: header.bottom
        
            Label {
                font.pixelSize: UI.FONT_DEFAULT
                text: currentGeocache ? currentGeocache.title : "None selected"
                anchors.left: parent.left
                anchors.right: parent.right
                wrapMode: Text.Wrap
            }

            WebView {
                anchors.left: parent.left
                anchors.right: parent.right
                
                html: "<html><body style='background-color: #eeeeee; font-family: sans-serif; font-size: 24px; padding: 0px; margin: 0px;'>" + currentGeocache.desc + "</body></html>"
                settings.javascriptEnabled: false
                settings.javaEnabled: false
                preferredWidth: parent.parent.width
            }
            
            Label {
                font.pixelSize: 20
                color: UI.COLOR_INFOLABEL
                text: "Drag down for hints"
            }
            
            Label {
                id: hints
                text: currentGeocache.hints || "No Hint"
                anchors.left: parent.left
                anchors.right: parent.right
                wrapMode: Text.Wrap
            }
        }
       
        clip: true
        contentWidth: width
        contentHeight: col1.height - hints.font.pixelSize
        
    }

}

