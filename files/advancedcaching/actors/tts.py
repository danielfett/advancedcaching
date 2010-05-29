import subprocess
import gobject

class TTS(gobject.GObject):

    def __init__(self, core):
        core.connect('good-fix', self.__tell_distance)
        gobject.GObject.__init__(self)

        try:
            self.proc = subprocess.Popen("espeak", stdin=subprocess.PIPE)
        except:
            raise Exception("You need to have espeak installed.")
            return

        self.proc.stdin.write("Espeak ready.\n")


    def __tell_distance(self, caller, gps_data, distance, bearing):
        output = "%d meters." % distance
        self.proc.stdin.write(output)
        print "Speaking: %s" % output
