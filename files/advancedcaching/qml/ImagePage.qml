import QtQuick 1.1
import com.nokia.meego 1.0
import "uiconstants.js" as UI

Page {
    id: tabImages
    orientationLock: PageOrientation.LockPortrait
    width: parent.width
    GeocacheHeader{
        cache: currentGeocache
        id: header
    }

    property bool imageOpen: false;

    Flow {
        anchors.top: header.bottom
        Repeater {
            model: currentGeocache.images// || emptyList
            delegate: Item {
                width: tabImages.width/3
                height: width
                property bool open: false
                id: imageItem 
                z: -1
                PolaroidImage {
                    scale: targetScale
                    source: model.image.url
                    text: "Dies ist ein Langer testtext. mit mehreren zeilen?" //model.image.name
                    maxWidth: tabImages.width - 8
                    maxHeight: tabImages.height - 8
                    property double targetScale: Math.min(Math.min(((parent.width - 8.0)/width), ((parent.height - 8.0)/height)), 1)
                    //property real targetX: width/2
                    //property real targetY: height/2
                    transform: Rotation {
                        id: trans;
                        angle: Math.random()*4 - 2
                        Behavior on angle { PropertyAnimation {} }
                    }
                    anchors.centerIn: parent
                    MouseArea {
                        anchors.fill: parent
                        onClicked: {
                            if (! (open || imageOpen)) {
                                imageOpen = true;
                                parent.scale = 1
                                var p = parent.parent.mapFromItem(tabImages, tabImages.width/2, tabImages.height/2)
                                parent.anchors.centerIn = null
                                parent.x = p.x - parent.width/2
                                parent.y = p.y - parent.height/2
                                parent.parent.z = 1000
                                trans.angle= 0
                                open = true
                            } else if (open) {
                                imageOpen = false;
                                parent.scale= parent.targetScale
                                trans.angle= Math.random()*4-2
                                open = false
                                parent.parent.z = -1
                                parent.x = parent.parent.width/2 - parent.width/2
                                parent.y = parent.parent.height/2 - parent.height/2
                            }
                        }
                    }
                    Behavior on x { PropertyAnimation { easing.type: Easing.InOutQuad } }
                    Behavior on y { PropertyAnimation { easing.type: Easing.InOutQuad } }
                    Behavior on scale { PropertyAnimation { easing.type: Easing.InOutQuad } }

                }

                Behavior on z { PropertyAnimation { easing.type: Easing.InOutQuad } }
            }
            onItemAdded: {
                imageOpen = false
            }
            onItemRemoved: {
                imageOpen = false
            }
        }
    }
}
