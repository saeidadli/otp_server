# -*- coding: utf-8 -*-

from setuptools import setup, find_packages


with open('README.rst') as f:
    readme = f.read()

with open('LICENSE.txt') as f:
    license = f.read()

setup(
    name='Python ArcGIS Convertor',
    version='0.1.0',
    description='A package to convert data between python and ArcGIS',
    long_description=readme,
    author='Saeid Adli',
    author_email='saeid.adli@gmail.com',
    url='spatialanalyst.ir',
    license=license,
    install_requires=[
        'pandas>=0.20.2',
        'numpy>=1.13.0',
        'geopandas>=0.2.1',
        'arcpy>=10.3.0',
    ],
    packages=find_packages(exclude=('tests', 'docs'))
)

