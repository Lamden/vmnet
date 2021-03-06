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

with open('.version', 'r+') as f:
    __version__ = f.read().strip().split('.')
with open('.version', 'w+') as f:
    __version__ = '.'.join(__version__[:-1] + [str(int(__version__[-1])+1)])
    f.write(__version__)

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
