import QtQuick 1.0
import com.nokia.meego 1.0
import "uiconstants.js" as UI
import QtWebKit 1.0

Page {
    GeocacheHeader{
        cache: currentGeocache
        id: header
    }
    anchors.fill: parent
    Label {
        wrapMode: Text.Wrap
        font.pixelSize: UI.FONT_DEFAULT
        text: currentGeocache ? currentGeocache.title : "None selected"
        width: parent.width
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: header.bottom
        anchors.leftMargin: 16
        anchors.rightMargin: 16
        id: title
    }


    Flickable {
        anchors.right: parent.right
        anchors.left: parent.left
        anchors.top: title.bottom
        anchors.bottom: parent.bottom
        anchors.margins: 16

        WebView {
            id: description
            html: "<html><body style='background-color: #F0F1F2; font-family: sans-serif; font-size: 24px;'>" + currentGeocache.desc + "</body></html>"
            settings.javascriptEnabled: false
            settings.javaEnabled: false
            preferredWidth: parent.parent.width
            onDoubleClick: {
                console.log(currentGeocache.desc)
            }
        }

        clip: true
        contentWidth: description.width
        contentHeight: description.height
    }


}

