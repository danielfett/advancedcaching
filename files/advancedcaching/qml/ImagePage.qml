import QtQuick 1.1
import com.nokia.meego 1.0
import "uiconstants.js" as UI

Page {
    id: tabImages
    orientationLock: PageOrientation.LockPortrait
    GeocacheHeader{
        cache: currentGeocache
        id: header
    }
    
    Flow {
        Repeater {
            anchors.top: header.bottom
            model: currentGeocache.images || emptyList
            delegate: Item { 
                width: tabImage.width/3
                height: width
                property bool open: False
                id: imageItem 
                PolaroidImage {
                    scale: (width/(parent.width - 8))
                    property double targetScale: 
                    transform: Rotation { id: trans; angle: Math.random()*4 - 2 }
                    anchors.centerIn: parent
                    MouseArea {
                        anchors.fill: parent
                        onClicked: {
                            if (! open) {
                                parent.anchors.centerIn: tabImages
                                parent.scale: 1
                                trans.angle: 0
                                open = true
                            } else {
                                parent.anchors.centerIn: imageItem
                                parent.scale: targetScale
                                trans.angle: Math.random()*4-2
                                open = false
                            }
                        }
                    }
                }
            }
        }
    }
}
