import QtQuick 1.0
import "uiconstants.js" as UI

Header {
    property variant cache: null

    text: (cache == null) ? "Select a geocache..." : (cache.type == "regular" ? "traditional" : cache.type) + " <b>" + cache.name + "</b>"
    color: (cache == null) ? "grey" : UI.getCacheColorBackground(cache)

    Image {
        source: "image://theme/icon-m-common-favorite" + (cache.marked ? "-mark" : "-unmark")
        anchors.top: parent.top
        anchors.topMargin: 8
        anchors.right: parent.right
        anchors.rightMargin: 8
        MouseArea {
            anchors.fill: parent
            onClicked: {
                cache.marked = ! cache.marked;
            }
        }
    }
}
