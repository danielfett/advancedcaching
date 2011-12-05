import QtQuick 1.1
import com.nokia.meego 1.0
import "uiconstants.js" as UI

Page {
    id: tabCamera
    orientationLock: PageOrientation.LockLandscape
    Rectangle {
        color: "black"
        anchors.fill: parent
    }

    Text {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.verticalCenter: parent.verticalCenter
        text: compass.azimuth

    }

    Loader {
        width: parent.width
        source: (tabGroup.currentTab == tabCamera) ? "CameraView.qml" : ""
    }

}
