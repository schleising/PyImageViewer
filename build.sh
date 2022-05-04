#!/bin/zsh
# Create a clean environment for the build
python3 -m venv .piv-build-env

# Acitivate the environment
source .piv-build-env/bin/activate

# Update pip if necessary
pip install -U pip

# Install the requirements in the new environment
pip install -r requirements.txt

# Remmove the dist and build directories
rm -rf dist
rm -rf build

# Run the script to create the app
python setup.py py2app

# Deactivate the environment
deactivate

# Remove the environment
rm -rf .piv-build-env
