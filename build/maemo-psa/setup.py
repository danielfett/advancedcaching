from distutils.core import setup
import os, sys, glob, shutil

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(name="agtl-maemo",
      scripts=[],
      version='___VERSION___',
      maintainer="daniel",
      maintainer_email="advancedcaching@fragcom.de",
      description="AGTL makes geocaching paperless!",
      long_description=read('agtl-maemo.longdesc'),
      data_files=[('share/applications/hildon',['agtl-maemo.desktop']),
                  ('share/icons/hicolor/64x64/apps', ['agtl-maemo.png']),
                  ('/opt/agtl-maemo/data', glob.glob('data/*')),
                  ('/opt/agtl-maemo/actors', glob.glob('actors/*.py')),
                  ('/opt/agtl-maemo/', glob.glob('*.py')),
                  ('/usr/bin/', ['agtl-maemo']),  ],)
