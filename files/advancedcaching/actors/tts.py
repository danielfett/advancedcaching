import subprocess

import gobject

class TTS(gobject.GObject):

    def __init__(self, core):
        gobject.GObject.__init__(self)

        self.gps_target_bearing_abs = None
        self.gps_target_distance = None
        self.proc = None

        self.timeout_event_id = None
        core.connect('good-fix', self.__on_good_fix)
        core.connect('no-fix', self.__on_no_fix)
        core.connect('settings-changed', self.__on_settings_changed)

    def __on_settings_changed(self, caller, settings, source):
        if 'tts_interval' in settings:
            self.__set_enabled(settings['tts_interval'])

    def __set_enabled(self, interval):
        if self.timeout_event_id != None:
            gobject.source_remove(self.timeout_event_id)
            self.timeout_event_id = None

        if interval > 0:
            gobject.timeout_add_seconds(interval, self.__tell)
            self.__connect()
        else:
            self.__disconnect()


    def __connect(self):
        if self.proc != None:
            return
        try:
            self.proc = subprocess.Popen("espeak", stdin=subprocess.PIPE)
            self.proc.stdin.write("Espeak ready.\n")
        except:
            self.proc = None
            raise Exception("Please install the 'espeak'-package.")

    def __disconnect(self):
        if self.proc != None:
            self.proc.terminate()

    def __on_good_fix(self, caller, gps_data, distance, bearing):
        self.gps_target_distance = distance
        self.gps_target_bearing_abs = bearing - gps_data.bearing

    def __tell(self):
        if self.gps_target_distance == None:
            output = "No Fix.\n"
        else:
            output = "%d meters, %d o'clock.\n" % (self.gps_target_distance, self.__degree_to_hour(self.gps_target_bearing_abs))
        self.proc.stdin.write(output)
        return True

    def __on_no_fix(self, caller, fix, msg):
        self.gps_target_distance = None
        self.gps_target_bearing_abs = None

    @staticmethod
    def __degree_to_hour(degree):
        ret = round((degree % 360) / 30.0)
        return ret if ret != 0 else 12