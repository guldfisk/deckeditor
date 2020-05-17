#!/usr/bin/env bash

rm -r ./package/
mkdir package
cp -r ./install/ ./package/
cp -r ./dist/editor/ ./package/install/embargoedit/
chmod a+x ./package/install/embargoedit/editor/editor
makeself ./package/install ./package/embargo-installer.sh "Embargo Editor" ./install_script.sh
