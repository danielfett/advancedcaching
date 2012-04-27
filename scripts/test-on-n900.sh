rsync -av --exclude '*.pyc' advancedcaching/* n900:advancedcaching/
ssh n900 "cd advancedcaching; run-standalone.sh python core.py --hildon -v "
