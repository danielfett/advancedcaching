import QtQuick 1.1
import com.nokia.meego 1.0
import "uiconstants.js" as UI


Page {
    id: listPage
    tools: commonTools
    orientationLock: PageOrientation.LockPortrait

    function showDetailsPage(page) {
        tabDetailsPageStack.push(page)
    }

    TabGroup {
        id: tabGroup
        currentTab: tabMap
        CompassPage {
            id: tabCompass
        }

        MapPage {
            id: tabMap
        }

        PageStack {
            id: tabDetailsPageStack
            anchors.fill: parent
            Component.onCompleted: {
                push(pageDetailsDefault)
            }
        }

        SettingsPage{
            id: tabSettings
        }

        VideoPage{
            id: tabCamera
        }

    }

    ToolBarLayout {
        id: commonTools
        visible: true
        ToolIcon {
            iconId: "toolbar-back" + ((tabDetailsPageStack.depth < 2) ? "-dimmed" : "")
            onClicked: {
                if (tabDetailsPageStack.depth > 1) tabDetailsPageStack.pop();
            }

        }

        ButtonRow {
            style: TabButtonStyle { }
            TabButton {
                //text: "Compass"
                iconSource: "../data/icon-m-toolbar-compass.png"
                tab: tabCompass
            }
            TabButton {
                //text: "Map"
                iconSource: "../data/icon-m-toolbar-map.png"
                tab: tabMap
            }
            TabButton {
                //text: "Details"
                tab: tabDetailsPageStack
                iconSource: "image://theme/icon-m-toolbar-search"
            }
            TabButton {
                //text: "Settings"
                tab: tabSettings
                iconSource: "image://theme/icon-m-toolbar-settings"
            }
            /*TabButton {
                tab: tabCamera
                iconSource: "image://theme/icon-m-viewfinder-camera-selected"
            }*/
        }
    }
}
