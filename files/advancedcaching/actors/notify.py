import gobject

class Notify(gobject.GObject):

    def __init__(self, core):
        gobject.GObject.__init__(self)

        self.gps_target_bearing_abs = None
        self.gps_target_distance = None
        #core.connect('good-fix', self.__on_good_fix)
        #core.connect('no-fix', self.__on_no_fix)
        #core.connect('settings-changed', self.__on_settings_changed)

    def __on_settings_changed(self, caller, settings, source):
        pass

    def __on_good_fix(self, caller, gps_data, distance, bearing):
        self.gps_target_distance = distance
        self.gps_target_bearing_abs = bearing - gps_data.bearing

    def __on_no_fix(self, caller, fix, msg):
        self.gps_target_distance = None
        self.gps_target_bearing_abs = None
