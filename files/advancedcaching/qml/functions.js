.pragma library

function formatDistance(d, controller) {
    if (! d) {
        return "0"
    }

    if (controller.distanceUnit == 'm') {
        if (d >= 1000) {
            return Math.round(d / 1000.0) + " km"
        } else if (d >= 100) {
            return Math.round(d) + " m"
        } else {
            return d.toFixed(1) + " m"
        }
    }
}

function formatBearing(b) {
    return Math.round(b) + "°"
}

function formatCoordinate(lat, lon, c) {
    return getLat(lat, c) + " " + getLon(lon, c)
}

function getDM(l) {
    var out = Array(3);
    out[0] = (l > 0) ? 1 : -1
    out[1] = ("00" + Math.floor(l)).substr(-3, 3)
    out[2] = ("00" + ((l - Math.floor(l)) * 60).toFixed(3)).substr(-6, 6)
    return out
}

function getValueFromDM(sign, deg, min) {
    return sign*(deg + (min/60))
}

function getLat(lat, controller) {
    var l = Math.abs(lat)
    var c = "S";
    if (lat > 0) {
        c = "N"
    }
    if (controller.coordinateFormat == "D") {
        return c + " " + l.toFixed(5) + "°"
    } else {
        return c + " " + Math.floor(l) + "° " + ((l - Math.floor(l)) * 60).toFixed(3) + "'"
    }
}

function getLon(lon, controller) {
    var l = Math.abs(lon)
    var c = "W";
    if (lon > 0) {
        c = "E"
    }
    if (controller.coordinateFormat == "D") {
        return c + " " + l.toFixed(5) + "°"
    } else {
        return c + " " + Math.floor(l) + "° " + ((l - Math.floor(l)) * 60).toFixed(3) + "'"
    }
}

function getMapTile(url, x, y, zoom) {
    return url.replace("%(x)d", x).replace("%(y)d", y).replace("%(zoom)d", zoom);
}
