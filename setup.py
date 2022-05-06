"""
This is a setup.py script generated by py2applet

Usage:
    python setup.py py2app
"""

from setuptools import setup

APP = ['main.py']
DATA_FILES = []

# A custom plist for file associations
Plist = dict(
    CFBundleDocumentTypes=[
        dict(
            CFBundleTypeExtensions=['jpeg','jpg'],
            CFBundleTypeName='JPEG image',
            CFBundleTypeRole='Viewer',
            ),
        dict(
            CFBundleTypeExtensions=['png'],
            CFBundleTypeName='PNG image',
            CFBundleTypeRole='Viewer',
            ),
        dict(
            CFBundleTypeExtensions=['gif'],
            CFBundleTypeName='GIF image',
            CFBundleTypeRole='Viewer',
            ),
        dict(
            CFBundleTypeExtensions=['webp'],
            CFBundleTypeName='WEBP image',
            CFBundleTypeRole='Viewer',
            ),
        ]
    )

OPTIONS = {
    # 'argv_emulation': True,
    'iconfile': 'ImageViewer/ImageViewer.icns',
    'plist': Plist,
}

setup(
    name='PyImageViewer',
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
    version='1.4.1',
)
