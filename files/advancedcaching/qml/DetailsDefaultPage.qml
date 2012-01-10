import QtQuick 1.0
import com.nokia.meego 1.0
import "uiconstants.js" as UI

Page {
    //id: pageDetailsDefault
    orientationLock: PageOrientation.LockPortrait
    GeocacheHeader{
        cache: currentGeocache
        id: header
    }

    Column {
        id: col1
        anchors.top: header.bottom
        spacing: 16
        anchors.left: parent.left
        anchors.right:  parent.right
        anchors.leftMargin: 16
        anchors.rightMargin: 16
        visible: currentGeocache != null

        Label {
            wrapMode: Text.Wrap
            font.pixelSize: UI.FONT_DEFAULT
            text: currentGeocache ? currentGeocache.title : ""
            width: parent.width
        }

        InfoLabel {
            name: "Created by"
            value: currentGeocache ? currentGeocache.owner : "unknown"
            width: col1.width
        }

        Item {
            height: Math.max(col1col1.height, col1col2.height)
            width: parent.width
            Column {
                id: col1col1
                anchors.left: parent.left
                anchors.top: parent.top
                width: parent.width/2
                spacing: 16
                StarRating{
                    id: rating1
                    rating: currentGeocache ? currentGeocache.terrain : -1
                    text: "Terrain"
                }
                SizeRating {
                    id: rating3
                    size: currentGeocache ? currentGeocache.size : -1
                    text: "Size"
                }

                Button {
                    text: "Set as target"
                    onClicked: {
                        controller.setAsTarget(currentGeocache)
                        showMessage("New Target set.")
                    }
                    width: col1.width/2
                }
            }
            Column {
                id: col1col2
                anchors.top: parent.top
                anchors.right: parent.right
                spacing: 16
                StarRating{
                    id: rating2
                    rating: currentGeocache ? currentGeocache.difficulty : -1
                    text: "Difficulty"
                }
                InfoLabel {
                    name: "Status"
                    value: (currentGeocache && currentGeocache.status == 0) ? "active" :
                                                                    (currentGeocache && currentGeocache.status == 1) ? "disabled" :
                    "archived";
                    color: (currentGeocache && currentGeocache.status == 1) ? "red" : "black";
                }
                /*
                InfoLabel {
                    name: "Created"
                    value: "2010-08-13?"
                }*/
                Button {
                    text: currentGeocache ? (currentGeocache.hasDetails ? "Update Details" : "Fetch details") : "Don't click!"
                    onClicked: {
                        controller.geocacheDownloadDetailsClicked(currentGeocache)
                    }
                    width: col1.width/2
                }
            }
        }



    }

    Column {
        anchors.bottom: parent.bottom
        spacing: 0
        width: parent.parent.width
        visible: currentGeocache != null

        ListButton {
            text: "Description"


            onClicked: {
                pageDescription.source = "DescriptionPage.qml";
                showDetailsPage(pageDescription.item);
            }

        }
        
        ListButton {
            text: "Images"
            onClicked: {
                pageImages.source = "ImagePage.qml";
                showDetailsPage(pageImages.item);
            }
            visible: (currentGeocache != null) && (currentGeocache.images.length > 0)
        }


        ListButton {
            text: "Coordinates"


            onClicked: {
                pageCoordinates.source = "CoordinatesPage.qml";
                showDetailsPage(pageCoordinates.item);
            }
        }

        ListButton {
            text: "Logs (" + (currentGeocache ? currentGeocache.logsCount : "-") + ")"

            onClicked: {
                pageLogs.source = "LogsPage.qml";
                showDetailsPage(pageLogs.item);
            }
        }
        
        
        ListButton {
            text: "Fieldnote"

            onClicked: {
                pageFieldnotes.source = "FieldnotesPage.qml";
                showDetailsPage(pageFieldnotes.item);
            }
        }

    }

    Loader {
        id: pageDescription
    }
    Loader {
        id: pageImages
    }
    Loader {
        id: pageCoordinates
    }
    Loader {
        id: pageLogs
    }
    Loader {
        id: pageFieldnotes
    }
    /*Connections {
        target: tabDetailsPageStack
        onDepthChanged: {
            if (tabDetailsPageStack.depth == 1) {
                pageDescription.source = "";
                pageCoordinates.source = "";
            }
        }
    }*/
    
    
    function openMenu() {
        if (rootWindow.pageStack.currentPage.openStackMenu) {
            rootWindow.pageStack.currentPage.openStackMenu();
        } else {
            openStackMenu();
        }
    }

    function openStackMenu() {
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
