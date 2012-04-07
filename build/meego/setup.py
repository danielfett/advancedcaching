from distutils.core import setup
import os, sys, glob, shutil

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(name="agtl-meego",
      scripts=['agtl-meego'],
      version='___VERSION___',
      maintainer="daniel",
      maintainer_email="advancedcaching@fragcom.de",
      description="AGTL makes geocaching paperless!",
      long_description=read('agtl-meego.longdesc'),
      data_files=[('share/applications',['agtl-meego.desktop']),
                  ('share/icons/hicolor/64x64/apps', ['agtl-meego.png']),
                  ('/opt/agtl-meego/qml', glob.glob('qml/*')),
                  ('/opt/agtl-meego/data', glob.glob('data/*')),
                  ('/opt/agtl-meego/actors', glob.glob('actors/*.py')),
                  ('/opt/agtl-meego/', glob.glob('*.py')),
                  ('/opt/agtl-meego/', ['splash.png']),  ],)
                  
                  
#shutil.rmtree('deb_dist/agtl-meego-0.8.0.7-meego1/debian/agtl-meego/usr/lib')
#shutil.rmtree('deb_dist/agtl-meego-0.8.0.7-meego1/debian/agtl-meego/usr/share/pyshared')
