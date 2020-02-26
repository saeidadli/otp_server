# -*- coding: utf-8 -*-

from setuptools import setup, find_packages


with open('README.md') as f:
    readme = f.read()

with open('LICENSE.txt') as f:
    license = f.read()

setup(
    name='otp-server',
    version='0.1.0',
    description='A package to use OTP for network analysis',
    long_description=readme,
    author='Saeid Adli',
    author_email='saeid.adli@gmail.com',
    url='spatialanalyst.ir',
    license=license,
    install_requires=[
        'geopandas>=0.4.10'
        'numpy>=1.13.3'
        'pandas>=0.23.4'
        'requests>=2.20.1'
        'shapely>=1.6.4'
    ],
    packages=find_packages(exclude=('tests', 'docs'))
)

