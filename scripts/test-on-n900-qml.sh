rsync -av --exclude '*.pyc' * n900:advancedcaching/
ssh n900 "cd advancedcaching; run-standalone.sh python core.py --qml-maemo -v "
