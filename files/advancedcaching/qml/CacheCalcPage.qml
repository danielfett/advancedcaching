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

    ListView {
        model: currentGeocache.varList || emptyList
        delegate:
            Label {
                text: "" + model.var.char + "=" + model.var.value
                }
                }
}

