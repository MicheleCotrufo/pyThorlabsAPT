import setuptools
from os import path

this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'),encoding ='unicode_escape') as f:
    long_description = f.read()

with open("requirements_strict.txt") as f:
    required_packages = f.read().splitlines()

setuptools.setup(name='pyThorlabsAPT',
      version='0.10',
      description='A python library/GUI to access and control motors via the APT protocol.',
      long_description=long_description,
      long_description_content_type='text/markdown',
      url='https://github.com/MicheleCotrufo/',
      author='Michele Cotrufo',
      author_email='michele.cotrufo@gmail.com',
      license='MIT',
      entry_points = {
        'console_scripts': ["pyThorlabsAPT = pyThorlabsAPT.main:main"],
      },
      packages=['pyThorlabsAPT'],
      include_package_data = True,
      install_requires= required_packages,
      zip_safe=False)