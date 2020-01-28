import os

from setuptools import setup


def package_files(directory):
    paths = []
    for path, directories, file_names in os.walk(directory):
        for filename in file_names:
            paths.append(os.path.join('..', path, filename))
    return paths

extra_files = package_files('deckeditor')

setup(
    name = 'deckeditor',
    version = '1.0',
    packages = ['deckeditor'],
    package_data={'': extra_files},
    include_package_data = True,
    install_requires = [
        'appdirs',
        'mtgorp @ https://github.com/guldfisk/mtgorp/tarball/master#egg=mtgorp-1.0',
        'mtgimg @ https://github.com/guldfisk/mtgimg/tarball/master#egg=mtgimg-1.0',
        'mtgqt @ https://github.com/guldfisk/mtgqt/tarball/master#egg=mtgqt-1.0',
        'orp @ https://github.com/guldfisk/orp/tarball/master#egg=orp-1.0',
        'draft @ https://github.com/guldfisk/draft/tarball/master#egg=draft-1.0',
        'lobbyclient @ https://github.com/guldfisk/lobbyclient/tarball/master#egg=lobbyclient-1.0',
        'cubeclient @ https://github.com/guldfisk/cubeclient/tarball/master#egg=cubeclient-1.0',
        'pillow',
        'promise',
        'PyQt5',
        'frozendict',
        'requests',
        'websocket-client',
        'websocket',
        'bidict',
    ],
)