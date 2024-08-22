#!/usr/bin/env bash
cd "$(dirname "${BASH_SOURCE[0]}")" || exit
cp ./embargo-edit.desktop /usr/share/applications/embargo-edit.desktop
chmod a+r /usr/share/applications/embargo-edit.desktop
cp -r ./embargoedit/ /usr/share/
chmod -R 777 /usr/share/embargoedit/
update-desktop-database /usr/share/applications
ln -s /usr/share/embargoedit/bin/embargo-edit.sh /usr/bin/embargo-edit
