from distutils.core import setup
from setuptools import setup
files = ['data/*']
setup(name='agtl',
	version='0.2.0',
	description='Towards paperless geocaching',
	author='Daniel Fett',
	author_email='agtl@fragcom.de',
	url='http://wiki.openmoko.org/wiki/Advanced_Geocaching_Tool_for_Linux',
	classifiers=[
		'Development Status :: 4 - Beta',
		'Environment :: X11 Applications',
		'Intended Audience :: End Users/Desktop',
		'License :: GNU General Public License (GPL)',
		'Operating System :: Linux',
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
	long_description = """Really long text here.""" 
	#
	#This next part it for the Cheese Shop, look a little down the page.
	#classifiers = []     
	) 

	#package_dir= {'agtl' : 'src'},
	packages = ['advancedcachinglib'],
	data_files = [('share/agtl/glade', glades), ('share/pixmaps', ['advancedcaching.png']), ('share/applications', ['advancedcaching.desktop'])],
	scripts = ['advancedcaching.py']
)
