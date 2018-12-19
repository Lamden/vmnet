python3 setup.py sdist bdist_wheel
source ~/.pypi
VERSION=$(cat .version)
twine upload -u ${USERNAME} -p ${PASSWORD} dist/*$VERSION*
