from setuptools import setup, find_packages
import sys, os

def include(path):
    all_files = []
    for root, dirs, files in os.walk(path):
        all_files.append(
            (root, [os.path.join(root, f) for f in files])
        )
    return all_files

def package_data(path):
    all_files = []
    for root, dirs, files in os.walk(path):
        all_files += [os.path.join(root, f) for f in files]
    return all_files

__version__ = '0.3.0'

setup(
    name='vmnet',
    version=__version__,
    entry_points={
        'console_scripts': [
            'vmnet=vmnet.launch:main',
            'vmnet-cloud=vmnet.cloud.launch:main'
        ],
    },
    description='A test-suite for distributed networks',
    packages=find_packages(exclude=['docs', 'examples']),
    install_requires=open('requirements.txt').readlines(),
    url='https://github.com/Lamden/vmnet',
    author='Lamden',
    author_email='team@lamden.io',
    zip_safe=True,
    include_package_data=True,
    classifiers=[
        'Programming Language :: Python :: 3.6',
    ],
)
