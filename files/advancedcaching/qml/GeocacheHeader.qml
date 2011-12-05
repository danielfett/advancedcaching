import QtQuick 1.0
import "uiconstants.js" as UI

Header {
    property variant cache: null

    text: ((cache.type == "regular" ? "traditional" : cache.type) || "") + " <b>" + (cache.name || "") + "</b>"
    color: UI.getCacheColorBackground(cache) || "grey"
}
