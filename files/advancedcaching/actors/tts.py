import subprocess
import gobject

class TTS(gobject.GObject):

    def __init__(self, core):
        self.gps_target_bearing = None
        self.gps_target_distance = None
        core.connect('good-fix', self.__on_good_fix)
        gobject.timeout_add_seconds(20, self.__tell)
        gobject.GObject.__init__(self)

        try:
            self.proc = subprocess.Popen("espeak", stdin=subprocess.PIPE)
        except:
            raise Exception("You need to have espeak installed.")
            return

        self.proc.stdin.write("Espeak ready.\n")

    def __on_good_fix(self, caller, gps_data, distance, bearing):
        self.gps_target_distance = distance
        self.gps_target_bearing = bearing

    def __tell(self):
        if self.gps_target_distance == None:
            return True
        output = "%d meters, %d o'clock.\n" % (self.gps_target_distance, self.__degree_to_hour(self.gps_target_bearing))
        self.proc.stdin.write(output)
        return True

    @staticmethod
    def __degree_to_hour(degree):
        ret = round((degree%360)/30.0)
        return ret if ret != 0 else 12