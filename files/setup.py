from distutils.core import setup
from setuptools import setup
files = ['data/*', 'actors/*.py', 'qt/*.py']
setup(name='agtl',
	version='0.8.0.4-freerunner0',
	description='Towards paperless geocaching',
	author='Daniel Fett',
	author_email='agtl@fragcom.de',
	url='http://wiki.openmoko.org/wiki/Advanced_Geocaching_Tool_for_Linux',
	classifiers=[
		'Development Status :: 4 - Beta',
		'Environment :: X11 Applications',
		'Intended Audience :: End Users/Desktop',
		'License :: OSI Approved :: GNU General Public License (GPL)',
		'Programming Language :: Python'
	],

	#Name the folder where your packages live:
	#(If you have other packages (dirs) or modules (py files) then
	#put them into the package directory - they will be found 
	#recursively.)
	packages = ['advancedcaching'],
	
	#'package' package must contain files (see list above)
	#I called the package 'package' thus cleverly confusing the whole issue...
	#This dict maps the package name =to=> directories
	#It says, package *needs* these files.
	package_data = {'advancedcaching' : files },
	
	#'runner' is in the root.
	scripts = ["agtl"],
	long_description = """AGTL, the all-in-one solution for on- and offline geocaching, makes geocaching paperless! 
It downloads geocaches including their description, hints, difficulty levels and images. No premium account needed. Searching for caches in your local db is a matter of seconds.
.
- Map view - supporting Open Street Maps and Open Cycle Maps by default, configurable for other map types, including google maps.
- GPS view - shows the distance and direction to the selected geocache.
- Cache details - all necessary details are available even in offline mode.
- Paperless geocaching features - take notes for a geocache on the go, see the hints and spoiler images, check the latest logs.
- Multicache calculation help - Let your phone do the math for you. Working for the most multi-stage geocaches, AGTL finds the coordinate calculations and let you enter the missing variables. (N900 only)
- Fieldnotes support - Ever came home after a long tour and asked yourself which geocaches you found? Never again: Log your find in the field and upload notes and log text when you're at home. Review them on the geocaching website and post the logs.
- Text-to-Speech-Feature! - Select a target, activate TTS and put your headphones on to enjoy completely stealth geocaching. (N900 only)
- Download map tiles for selected zoom levels - for offline use.
- Advanced waypoint handling - AGTL finds waypoints in the geocache descriptions, in the list of waypoints and even in your notes. For your convenience, they're displayed on the map as well - see where you have to go next.
- Search for places - in the geonames.org database to navigate quickly. (N900 only)
- Sun compass - Compensates the lack of a magnetic compass. (N900 only)
- Instant update feature - Follow web site updates as soon as possible.
.
AGTL is Open source and in active development.""" 
	#
	#This next part it for the Cheese Shop, look a little down the page.
	#classifiers = []     
	
)
