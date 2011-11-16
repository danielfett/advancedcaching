import QtQuick 1.1
import com.nokia.meego 1.0
import "uiconstants.js" as UI

PageStackWindow {
    id: rootWindow
    //property int pageMargin: 16

    // ListPage is what we see when the app starts, it links to
    // the component specific pages
    initialPage: MainPage { }

    // These tools are shared by most sub-pages by assigning the
    // id to a page's tools property
    //platformStyle: PageStackWindowStyle {
    //    background: COLOR_BACKGROUND
    //}

}
