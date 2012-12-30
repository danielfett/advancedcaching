import com.nokia.meego 1.0
import QtQuick 1.1

Sheet {
    id: test
    acceptButtonText: "Save"
    rejectButtonText: "Close"


    content: [
        MouseArea { // to keep the dialog from closing when the user clicks on the background
            anchors.fill: test
            onClicked: {  }
        },
            
        
        TextArea {
            id: fieldnoteText
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.leftMargin: 16
            anchors.rightMargin: 16
            anchors.bottom: parent.bottom
            anchors.topMargin: 16
            anchors.bottomMargin: 16
            textFormat: TextEdit.PlainText
            wrapMode: TextEdit.Wrap
        }

    ]
    
    function getValue() {
        return fieldnoteText.text;
    }
    
    function setValue(text) {
        fieldnoteText.text = text;
    }
}
