# -*- mode: python ; coding: utf-8 -*-

import importlib
import os


block_cipher = None

package_imports = (
    ('mtgimg', ('cardback',), 'mtgimg/cardback'),
    ('magiccube', ('resources',), 'magiccube/resources'),
    ('mtgorp', ('db/limited/data.json',), 'mtgorp/db/limited'),
)

datas = [
    ('deckeditor/resources/', 'deckeditor/resources'),
    # ('./build_venv/lib/python3.8/site-packages/frozendict/VERSION', 'frozendict/'),
]
for package, paths, out_path in package_imports:
    package_root = os.path.dirname(importlib.import_module(package).__file__)
    datas.extend(
        (os.path.join(package_root, f), out_path)
        for f in
        paths
    )

a = Analysis(
    ['deckeditor/editor.py'],
    pathex = ['/home/phdk/PycharmProjects/deckeditor'],
    binaries = [],
    hiddenimports = [
        'ijson.backends.python',
        'sqlalchemy.ext.baked',
        'sqlalchemy.interfaces',
        'pyqtgraph.graphicsItems.ViewBox.axisCtrlTemplate_pyqt5',
        'pyqtgraph.graphicsItems.PlotItem.plotConfigTemplate_pyqt5',
        'pyqtgraph.imageview.ImageViewTemplate_pyqt5',
    ],
    hookspath = [],
    runtime_hooks = [],
    excludes = [],
    win_no_prefer_redirects = False,
    win_private_assemblies = False,
    cipher = block_cipher,
    noarchive = False,
    datas = datas,
)
pyz = PYZ(
    a.pure, a.zipped_data,
    cipher = block_cipher,
)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries = True,
    name = 'editor',
    debug = False,
    bootloader_ignore_signals = False,
    strip = False,
    upx = True,
    console = True,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip = False,
    upx = True,
    upx_exclude = [],
    name = 'editor',
)
