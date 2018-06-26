import os

from setuptools import setup

setup(
	name = 'deckeditor',
	version = '1.0',
	packages = ['deckeditor'],
	dependency_links = [
		'https://github.com/guldfisk/mtgorp/tarball/master#egg=mtgorp-1.0',
		'https://github.com/guldfisk/orp/tarball/master#egg=orp-1.0',
		'https://github.com/guldfisk/orp/tarball/master#egg=mtgimg-1.0',
	],
	package_data = {
		'deckeditor': [os.path.join('resources', '*.*')],
	},
	include_package_data = True,
	install_requires = [
		'appdirs',
		'mtgorp',
		'mtgimg',
		'orp',
		'pillow',
		'promise',
		'PyQt5',
	],
)