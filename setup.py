from setuptools import setup, find_packages
import sys

__version__ = '0.2.30'
setup(
    name='vmnet',
    version=__version__,
    entry_points={
        'console_scripts': ['vmnet=vmnet.launch:main'],
    },
    description='A test-suite for distributed networks',
    packages=find_packages(exclude=['docs', 'examples']),
    install_requires=open('requirements.txt').readlines(),
    url='https://github.com/Lamden/vmnet',
    author='Lamden',
    email='team@lamden.io',
    include_package_data=True,
    classifiers=[
        'Programming Language :: Python :: 3.6',
    ],
)
