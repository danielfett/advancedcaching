#!/bin/bash
set -e
EXE=advancedcaching/core.py
$EXE update
$EXE import --skip-found --in 'q:Hemmersdorf' 'q:Niedaltdorf'
$EXE import --around 'q:Olewig' 0.6
# The routing option is not maintained at the moment
# $EXE import --at-route 'q:Olewig' 'q:Trier' 0.1
$EXE filter -f -s small do --print
$EXE filter -t 2.0 do --fetch-details
$EXE filter -o r:'.*ebhamste.*' do --command "echo %s"
$EXE filter -d 2.0 do --commands "echo {name} {difficulty} {size} {owner}"
