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

    }

    ToolBarLayout {
        id: commonTools
        visible: true
        ToolIcon {
            iconId: "toolbar-back"
            onClicked: {
                if (tabDetailsPageStack.depth > 1) tabDetailsPageStack.pop();
            }
        }

        ButtonRow {
            style: TabButtonStyle { }
            TabButton {
                text: "Compass"
                tab: tabCompass
            }
            TabButton {
                text: "Map"
                tab: tabMap
            }
            TabButton {
                text: "Details"
                tab: tabDetailsPageStack
            }
            TabButton {
                //text: "Settings"
                tab: tabSettings
                iconSource: "image://theme/icon-m-toolbar-view-menu"
            }
        }
    }
}
