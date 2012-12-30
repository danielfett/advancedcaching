import com.nokia.meego 1.0
import QtQuick 1.1

Sheet {
    id: test
    //anchors.centerIn: parent
    acceptButtonText: "Save"
    rejectButtonText: "Close"
    //titleText: "Edit Coordinate"


    content: [
        MouseArea { // to keep the dialog from closing when the user clicks on the background
            anchors.fill: cs
            onClicked: {  }
        },
            
        Label {
            id: intro
            text: "This is the default text presented to you when creating a field note or log. You can use the following placeholders: %(machine)s = device name, %c = Date and Time, %x = Date, %X = Time and more, just search the web for strftime."
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.leftMargin: 16
            anchors.rightMargin: 16
            anchors.topMargin: 16
        },
        
        TextArea {
            id: fieldnoteText
            anchors.top: intro.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.leftMargin: 16
            anchors.rightMargin: 16
            anchors.bottom: parent.bottom
            anchors.topMargin: 16
            anchors.bottomMargin: 16
            textFormat: TextEdit.PlainText
            wrapMode: TextEdit.Wrap
            text: settings.optionsDefaultLogText
            
        }

    ]
    
    function getValue() {
        return fieldnoteText.text;
    }
}
