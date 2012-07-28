import QtQuick 1.0
import com.nokia.meego 1.0
import "uiconstants.js" as UI

Page {
    orientationLock: PageOrientation.LockPortrait
    Header{
        text: "List Geocaches"
        id: header
    }

    Column {
        anchors.top: header.bottom
        //anchors.topMargin: 8
        spacing: 0
        width: parent.parent.width

        ListButton {
            text: "...in current map view"

            onClicked: {
                pageGeocacheList.source = "GeocacheListPage.qml";
                pageGeocacheList.item.title = "Geocaches in Map";
                pageGeocacheList.item.model = tabMap.geocacheModel;
                pageGeocacheList.item.model.sort(0, gps);
                showDetailsPage(pageGeocacheList.item);
            }
            height: 70
        }

        ListButton {
            text: "...having Fieldnotes"

            onClicked: {
                pageGeocacheList.source = "GeocacheListPage.qml";
                pageGeocacheList.item.title = "Geocaches with Fieldnotes";
                pageGeocacheList.item.model = controller.getGeocachesWithFieldnotes();
                pageGeocacheList.item.model.sort(0, gps);
                showDetailsPage(pageGeocacheList.item);
            }
            height: 70
        }

        ListButton {
            text: "...in Favorites"

            onClicked: {
                pageGeocacheList.source = "GeocacheListPage.qml";
                pageGeocacheList.item.title = "Favorite Geocaches";
                pageGeocacheList.item.model = controller.getMarkedGeocaches();
                pageGeocacheList.item.model.sort(0, gps);
                showDetailsPage(pageGeocacheList.item);
            }
            height: 70
        }
        
        ListButton {
            text: "Last viewed"

            onClicked: {
                pageGeocacheList.source = "GeocacheListPage.qml";
                pageGeocacheList.item.title = "History";
                pageGeocacheList.item.model = controller.getLastViewedGeocaches();
                pageGeocacheList.item.model.sort(4, gps);
                showDetailsPage(pageGeocacheList.item);
            }
            height: 70
        }
        
        ListButton {
            text: "Recently updated"

            onClicked: {
                pageGeocacheList.source = "GeocacheListPage.qml";
                pageGeocacheList.item.title = "Recently Updated";
                pageGeocacheList.item.model = controller.getLastUpdatedGeocaches();
                pageGeocacheList.item.model.sort(5, gps);
                showDetailsPage(pageGeocacheList.item);
            }
            height: 70
        }
    }



    Loader {
        id: pageGeocacheList
    }


    function openMenu() {
        menu.open();
    }

    Menu {
        id: menu
        visualParent: parent

        MenuLayout {
            //MenuItem { text: currentGeocache.found ? "Mark Not Found" : "Mark Found"; }
            MenuItem { text: "Settings"; onClicked: { showSettings(); } }
        }
    }
}
