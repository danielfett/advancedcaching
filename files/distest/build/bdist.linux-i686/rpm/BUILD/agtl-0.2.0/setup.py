__author__="daniel"
__date__ ="$05.09.2009 15:36:19$"

from distutils.core import setup
import glob

glades = glob.glob('glade/*.glade')

setup(name='agtl',
    version='0.2.0',
    description='Towards paperless geocaching',
    author='Daniel Fett',
    author_email='agtl@fragcom.de',
    url='',
    classifiers=[
            'Development Status :: 4 - Beta',
            'Environment :: X11 Applications',
            'Intended Audience :: End Users/Desktop',
            'License :: GNU General Public License (GPL)',
            'Operating System :: Linux',
            'Programming Language :: Python'
            ],
    #package_dir= {'agtl' : 'src'},
    packages = ['advancedcachinglib'],
    data_files = [('share/agtl/glade', glades), ('share/pixmaps', ['advancedcaching.png']), ('share/applications', ['advancedcaching.desktop'])],
    scripts = ['advancedcaching.py']
    )