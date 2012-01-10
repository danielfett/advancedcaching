import QtQuick 1.1
import com.nokia.meego 1.0
import "uiconstants.js" as UI

Page {
    tools: commonTools
    GeocacheHeader{
        cache: currentGeocache
        id: listHeader
    }


    ListView {
        anchors.top: listHeader.bottom
        anchors.leftMargin: 16
        anchors.rightMargin: 16
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom:  parent.bottom
        anchors.topMargin: 16
        model: currentGeocache.logs || emptyList
        clip: true
        delegate: Column {
            height: rw.height + description.height + 16 * 2
            spacing: 16
            width: parent.width
            Row {
                id: rw
                spacing: 8
                Image {
                    source: "../data/" + model.log.iconBasename + ".png"
                    id: icon
                    smooth: true
                    width: sourceSize.width * 1.5
                    height:sourceSize.height * 1.5
                }

                Label {
                    text: model.log.year + "-" + model.log.month + "-" + model.log.day + " by " + model.log.finder
                    font.weight: Font.Light
                    font.pixelSize: 22
                    visible: text != ""
                    width: parent.parent.width - rw.spacing - icon.width
                }
            }

            Label {
                id: description
                font.weight: Font.Light
                text: model.log.text
                wrapMode: Text.Wrap
                font.pixelSize: 22
                color: theme.inverted ? UI.COLOR_DESCRIPTION_NIGHT : UI.COLOR_DESCRIPTION
                width: parent.parent.width - 2*16
            }


        }
    }

}
