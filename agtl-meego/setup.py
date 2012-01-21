from distutils.core import setup
import os, sys, glob

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(name="agtl-meego",
      scripts=['agtl-meego'],
      version='0.8.0.7-meego1',
      maintainer="daniel",
      maintainer_email="advancedcaching@fragcom.de",
      description="AGTL makes geocaching paperless!",
      long_description=read('agtl-meego.longdesc'),
      data_files=[('share/applications',['agtl-meego.desktop']),
                  ('share/icons/hicolor/64x64/apps', ['agtl-meego.png']),
                  ('share/agtl-meego/qml', glob.glob('qml/*')),
                  ('share/agtl-meego/data', glob.glob('data/*')),
                  ('share/agtl-meego/actors', glob.glob('actors/*.py')),
                  ('share/agtl-meego/', glob.glob('*.py')),
                  ('share/agtl-meego/', ['splash.png']),  ],)
