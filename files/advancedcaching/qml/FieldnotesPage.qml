import QtQuick 1.0
import com.nokia.meego 1.0
import "uiconstants.js" as UI

Page {
        
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
        anchors.top: header.bottom
    
        Label {
            font.pixelSize: UI.FONT_DEFAULT
            text: "Write Fieldnote"
            anchors.left: parent.left
            anchors.right: parent.right
            wrapMode: Text.Wrap
        }
        
        Label {
            font.pixelSize: 20
            wrapMode: Text.Wrap
            anchors.left: parent.left
            anchors.right: parent.right
            text: "Fieldnotes are temporary log entries, which can be reviewed and submitted as a regular log later on. After uploading, you will find them in your account overview on the web page. If you don't upload them now, they are stored here."
        }
        
        Item { 
            anchors.left: parent.left
            anchors.right: parent.right
            height: 60
            
            BorderImage {
                id: background
                anchors.fill: parent
                anchors.leftMargin: -16
                anchors.rightMargin: -16
                visible: mouseArea.pressed
                source: "image://theme/meegotouch-list-background-pressed-center"
            }
             
            Label {
                anchors.verticalCenter: parent.verticalCenter
                text: logModel.get(currentGeocache.logas).name
                anchors.left: parent.left
            }
            
            Image {
                 id: arrow
                 source: "image://theme/icon-m-common-drilldown-arrow" + (theme.inverted ? "-inverse" : "")
                 anchors.right: parent.right;
                 anchors.verticalCenter: parent.verticalCenter
            }
            
            MouseArea {
                id: mouseArea
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
        onActiveFocusChanged: {
            if (! activeFocus) {
                saveFieldnote();
            }
        }
        textFormat: TextEdit.PlainText
        wrapMode: TextEdit.Wrap
        text: currentGeocache.fieldnotes
        
        anchors.leftMargin: 16
        anchors.rightMargin: 16
    }
    
    Row {
        id: row1
        Button { 
            text: "Upload all Fieldnotes now"
            width: 4 * parent.width/5
            onClicked: {
                controller.uploadFieldnotes();
            }
        }
        
        /*Label {
            font.pixelSize: 20
            wrapMode: Text.Wrap
            text: "To upload fielnotes later, use the menu."
            width: parent.width/2
        }*/      
        
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
            saveFieldnote();
        }
    }
           
    ListModel {
        id: logModel
        ListElement{ name: "Don't upload Fieldnote" }
        ListElement{ name: "Found it!" }
        ListElement{ name: "Didn't find it!" }
        ListElement{ name: "Write a note" }
    }
    
    function saveFieldnote() {
        var logas = Math.max(logAsDialog.selectedIndex, 0)
        var text = fieldnoteText.text
        currentGeocache.setFieldnote(logas, text)
    }
}

