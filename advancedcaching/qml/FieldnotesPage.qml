import QtQuick 1.0
import com.nokia.meego 1.0
import "uiconstants.js" as UI
import "functions.js" as F

Page {
    tools: commonTools

    GeocacheHeader{
        cache: currentGeocache
        id: header
    }
    
    Column {
        id: col1
        spacing: 16
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: 16
        anchors.rightMargin: 16
        anchors.topMargin: 8
        anchors.top: header.bottom

    
        Row {
            spacing: 16
            Image {
                id: fieldnoteHelp
                source: "image://theme/icon-m-content-description" + (theme.inverted ? "-inverse" : "")
                height: 36
                width: 36
                MouseArea {
                    anchors.fill: parent
                    onClicked: { infoDialog.open() }
                }
            }
            
            Label {
                font.pixelSize: UI.FONT_DEFAULT
                text: "Fieldnote"
                wrapMode: Text.Wrap
            }
            
            Switch {
                onCheckedChanged: {
                    // GeocacheCoordinate.UPLOAD_AS_FIELDNOTE == 0
                    // GeocacheCoordinate.UPLOAD_AS_LOG == 1
                    var value = checked ? 1 : 0;
                    if (currentGeocache.uploadAs != value) currentGeocache.uploadAs = value;
                }
                checked: (currentGeocache.uploadAs == 1)
                            
            }
            
            Label {
                font.pixelSize: UI.FONT_DEFAULT
                text: "Log Entry"
                wrapMode: Text.Wrap
            }
        }
        
        
        Item { 
            anchors.left: parent.left
            anchors.right: parent.right
            height: 60
            
            BorderImage {
                anchors.fill: parent
                anchors.leftMargin: -16
                anchors.rightMargin: -16
                visible: mouseArea2.pressed
                source: "image://theme/meegotouch-list-background-pressed-center"
            }

            Label {
                anchors.verticalCenter: parent.verticalCenter
                text: logModel.get(currentGeocache.logas).name
                anchors.left: parent.left
            }
            
            Image {
                source: "image://theme/icon-m-common-drilldown-arrow" + (theme.inverted ? "-inverse" : "")
                anchors.right: parent.right;
                anchors.verticalCenter: parent.verticalCenter
            }
            
            MouseArea {
                id: mouseArea2
                anchors.fill: parent
                onClicked: { logAsDialog.open() }
            }
        }
        

    }
    
    
    TextArea {
        id: fieldnoteText
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: col1.bottom
        anchors.topMargin: 8
        anchors.bottom: row1.top
        anchors.bottomMargin: 8
        textFormat: TextEdit.PlainText
        wrapMode: TextEdit.Wrap
        text: currentGeocache.fieldnotes
        enabled: false
        
        anchors.leftMargin: 16
        anchors.rightMargin: 16
        
    }
    
    Row {
        id: row1
        Button { 
            text: "Upload all Logs/Fieldnotes now"
            width: parent.width
            onClicked: {
                controller.uploadFieldnotes();
            }
        }
        
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottomMargin: 16
        anchors.leftMargin: 16
        anchors.rightMargin: 16
    }
    
    SelectionDialog {
        id: logAsDialog
        model: logModel
        onSelectedIndexChanged: {
            if (selectedIndex != currentGeocache.logas) {
                currentGeocache.logas = Math.max(logAsDialog.selectedIndex, 0);
            }
        }
    }

    QueryDialog {
        id: infoDialog
        titleText: "About Fieldnotes"

        content: [Label {
            font.pixelSize: 26
            wrapMode: Text.Wrap
            anchors.left: parent.left
            anchors.right: parent.right
            text: "Fieldnotes are temporary log entries, which can be reviewed and submitted as regular logs later on.<br><br>After uploading, you will find them in your account overview on the web page. If you don't upload them now, they are stored here for later uploading."
        }]
    }
    
    
    MouseArea {
        anchors.fill: fieldnoteText
        onClicked: {
            fieldnoteDialogLoader.source = "FieldnoteDialog.qml";
            fieldnoteDialogLoader.item.accepted.connect(function() {
                currentGeocache.fieldnotes = fieldnoteDialogLoader.item.getValue();
            });
            fieldnoteDialogLoader.item.setValue(currentGeocache.fieldnotes ? currentGeocache.fieldnotes : settings.getFieldnoteDefaultText());
            fieldnoteDialogLoader.item.open();
        }
    }

    Connections {
        target: rootWindow
        onCurrentGeocacheChanged: {
            logAsDialog.selectedIndex = currentGeocache.logas
        }

    }

    ListModel {
        id: logModel
        ListElement{ name: "Don't upload" }
        ListElement{ name: "Found it!" }
        ListElement{ name: "Didn't find it!" }
        ListElement{ name: "Write a note" }
    }
    

    function openMenu() {
        menu.open();
    }
    
    
    Loader {
        id: fieldnoteDialogLoader
    }
    

    Menu {
        id: menu
        visualParent: parent

        MenuLayout {
            MenuItem { text: "Settings"; onClicked: { showSettings(); } }
        }

        MenuLayout {
            MenuItem { text: "Share Find on Twitter"; onClicked: {
                    var title = currentGeocache.title.trunc(90, true);
                    var text = encodeURIComponent("I just found the #Geocache '" + title + "' #agtl #n9");
                    var url = encodeURIComponent(currentGeocache.url);
                    Qt.openUrlExternally("https://twitter.com/share?url=" + url + "&text=" + text);
                } }
        }
    }
}

