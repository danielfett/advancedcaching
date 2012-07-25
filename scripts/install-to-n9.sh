#!/bin/bash
scp $1 n9:agtl-install.deb
ssh n9 "devel-su -c 'dpkg -i /home/user/agtl-install.deb'"
