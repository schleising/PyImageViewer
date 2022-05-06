#!/bin/zsh
# Create a clean environment for the build
python3 -m venv .piv-build-env

# Acitivate the environment
source .piv-build-env/bin/activate

# Update pip if necessary
pip install -U pip

# Install the requirements in the new environment
pip install -r requirements.txt

# Remove the dist and build directories
rm -rf dist
rm -rf build

# Run the script to create the app
python setup.py py2app

# Deactivate the environment
deactivate

# Remove the environment
rm -rf .piv-build-env

# Remove the build directory
rm -rf build

# Zip the application
tar -czf dist/PyImageViewer.app.tar.gz dist/PyImageViewer.app

# Remove the existing Application and zip file from Downloads
rm -rf ~/Downloads/PyImageViewer.app
rm ~/Downloads/PyImageViewer.app.tar.gz

# Move the Application and zip file into Downloads
mv dist/PyImageViewer.app.tar.gz dist/PyImageViewer.app ~/Downloads

# Remove the dist folder
rm -rf dist
