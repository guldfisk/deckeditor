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
	dependency_links = [
		'https://github.com/guldfisk/mtgorp/tarball/master#egg=mtgorp-1.0',
		'https://github.com/guldfisk/orp/tarball/master#egg=orp-1.0',
		'https://github.com/guldfisk/mtgimg/tarball/master#egg=mtgimg-1.0',
	],
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