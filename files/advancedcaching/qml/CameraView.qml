import QtQuick 1.1
import QtMultimediaKit 1.1

Camera {
     id: camera
     visible: (tabGroup.currentTab == tabCamera)
     y: 0
     width: parent.width
     anchors.horizontalCenter: parent.horizontalCenter
     captureResolution: "1152x648"
     focus: visible
     whiteBalanceMode: Camera.WhiteBalanceAuto
     exposureCompensation: -1.0
     state: (tabGroup.currentTab == tabCamera) ? Camera.ActiveState : Camera.LoadedState


     property int apertureAngle: 70

     function angleToScreenpoint (a) {
         return camera.width * (a/apertureAngle)
     }
     property int angle: compass.azimuth - 90 // in landscape mode, compass is shifted 90 degress
     property real leftDegrees: Math.floor((angle - apertureAngle/2)/10)*10
     property real offsetPixels: angleToScreenpoint(angle - leftDegrees) - camera.width/2
     Repeater {
         model: Math.round(apertureAngle/10)
         delegate: Column {
             x: angleToScreenpoint(index * 10) - camera.offsetPixels
             y: 10
             Label {
                 color: "#00ff00"
                 text: index*10 + camera.leftDegrees
                 font.pixelSize: 20
                 x: -width/2
             }
         }
     }

     Rectangle {
         border.color: "#00ff00"
         border.width: 2
         height: 15
         width: 2
         x: angleToScreenpoint(apertureAngle/2)
         y: 30
     }

}
