TYPE_UNKNOWN = 'unknown'

TYPE_REGULAR = 'regular'
TYPE_MULTI = 'multi'
TYPE_MYSTERY = 'mystery'
TYPE_LETTERBOX = 'letterbox'
TYPE_WHERIGO = 'wherigo'
TYPE_EVENT = 'event'
TYPE_MEGAEVENT = 'megaevent'
TYPE_TRASHEVENT = 'trashevent'
TYPE_EARTH = 'earth'

# Grandfathered types of caches
TYPE_VIRTUAL = 'virtual'
TYPE_WEBCAM = 'webcam'

TYPE_LABELS = {
    TYPE_UNKNOWN: 'Unknown Cache',
    TYPE_REGULAR: 'Traditional Cache',
    TYPE_MULTI: 'Multi-cache',
    TYPE_MYSTERY: 'Mystery Cache',
    TYPE_LETTERBOX: 'Letterbox Hybrid',
    TYPE_WHERIGO: 'Wherigo Cache',
    TYPE_EVENT: 'Event Cache',
    TYPE_MEGAEVENT: 'Mega-Event Cache',
    TYPE_TRASHEVENT: 'Cache In Trash Out Event',
    TYPE_EARTH: 'EarthCache',
    TYPE_VIRTUAL: 'Virtual Cache',
    TYPE_WEBCAM: 'Webcam Cache',
}

TYPES = TYPE_LABELS.keys()

# Map name of image at geocaching.com to cache type.
GC_TYPE_MAP = {
    2: TYPE_REGULAR,
    3: TYPE_MULTI,
    8: TYPE_MYSTERY,
    5: TYPE_LETTERBOX,
    1858: TYPE_WHERIGO,
    6: TYPE_EVENT,
    453: TYPE_MEGAEVENT,
    13: TYPE_TRASHEVENT,
    137: TYPE_EARTH,
    4: TYPE_VIRTUAL,
    11: TYPE_WEBCAM,
}
