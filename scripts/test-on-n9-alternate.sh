rsync -av --exclude '*.pyc' * n9d:advancedcaching/
ssh n9d "source /tmp/session_bus_address.user; cd advancedcaching; DISPLAY=:0 python ./core.py --qml -v"
