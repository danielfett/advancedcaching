import QtQuick 1.0
import "uiconstants.js" as UI

Header {
    property variant cache: null

    text: (cache == null) ? "Select a geocache..." : (cache.type == "regular" ? "traditional" : cache.type) + " <b>" + cache.name + "</b>"
    color: (cache == null) ? "grey" : UI.getCacheColorBackground(cache)
}
