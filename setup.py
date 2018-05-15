from setuptools import setup, find_packages

__version__ = '0.0.1'

setup(
    name='vmnet',
    version=__version__,
    packages=find_packages(exclude=['docs', 'tests', 'examples']),
    install_requires=open('requirements.txt').readlines(),
    long_description=open('README.md').read(),
    url='https://github.com/Lamden/vmnet',
    author='Lamden',
    email='team@lamden.io',
    classifiers=[
        'Programming Language :: Python :: 3.6',
    ],
)
