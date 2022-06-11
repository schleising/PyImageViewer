from enum import Enum, auto
import sys
import logging
from pathlib import Path

import pyglet

from ImageViewer.Viewer import Viewer
from ImageViewer.FileBrowser import FileBrowser
from ImageViewer.FileTypes import supportedExtensions
from ImageViewer.Logger import Logger

class ViewerMode(Enum):
    FileBrowserMode = auto()
    ImageViewerMode = auto()

class ImageViewer(pyglet.window.Window):
    def __init__(self, fullScreenAllowed: bool) -> None:
        # Call base class init
        super(ImageViewer, self).__init__()

        # Create a logger instance
        logger = Logger()

        # Get the logger queue
        logQueue = logger.messageQueue

        # Log that the application has started
        logQueue.put_nowait(('Application Started', logging.INFO))

        if len(sys.argv) > 1:
            # If there is an image on the command line, get it
            imagePath = Path(sys.argv[1])
        else:
            # Otherwise try to default to the Pictures folder
            imagePath = Path.home() / 'Pictures'

            # If Pictures does not exist use the user home folder as the default instead
            if not imagePath.exists():
                imagePath = Path.home()

        # Check whether the path is a file or folder
        if imagePath.is_file():
            if imagePath.suffix.lower() in supportedExtensions.values():
                # If it's an image file start directly in the viewer
                self.viewerMode = ViewerMode.ImageViewerMode
            else:
                # If it's not and image file, start the file browser in the parent of this file
                imagePath = imagePath.parent
                self.viewerMode = ViewerMode.FileBrowserMode
        else:
            # If it's a folder start in the browser in this folder
            self.viewerMode = ViewerMode.FileBrowserMode

        # Control whether the windows are allowed to be full screen
        self.fullScreenAllowed = fullScreenAllowed

        # Set window to full screen
        self.set_fullscreen(self.fullScreenAllowed)

        # Create a viewer
        self.viewer = Viewer(self.width, self.height, self, logQueue)

        # Create a file browser
        self.fileBrowser = FileBrowser(imagePath, self.width, self.height, self, self.viewer.SetupImagePathAndLoadImage, logQueue)

        # Let the viewer have access to the file browser
        self.viewer.fileBrowser = self.fileBrowser

        if self.viewerMode == ViewerMode.ImageViewerMode:
            # If we're starting in the viewer load the image
            self.viewer.SetupImagePathAndLoadImage(imagePath)

        # Log that the main loop is starting
        logQueue.put_nowait(('Starting Pyglet mainloop', logging.DEBUG))

        # Run the app
        pyglet.app.run()

        # Put None onto the thumbnail server queue to stop the process
        self.fileBrowser.thumbnailServer.toTS.put_nowait((None, None))

        # Log that the application is closing
        logQueue.put_nowait(('Exiting', logging.INFO))

    def toggleViewer(self) -> None:
        if self.viewerMode == ViewerMode.FileBrowserMode:
            self.viewerMode = ViewerMode.ImageViewerMode
        else:
            self.viewerMode = ViewerMode.FileBrowserMode

    def on_draw(self):
        if self.viewerMode == ViewerMode.ImageViewerMode:
            self.viewer.on_draw()
        else:
            self.fileBrowser.on_draw()

    def on_key_press(self, symbol, modifiers):
        if self.viewerMode == ViewerMode.ImageViewerMode:
            self.viewer.on_key_press(symbol, modifiers)
        else:
            self.fileBrowser.on_key_press(symbol, modifiers)

    def on_key_release(self, symbol, modifiers):
        if self.viewerMode == ViewerMode.ImageViewerMode:
            self.viewer.on_key_release(symbol, modifiers)

    def on_mouse_motion(self, x, y, dx, dy):
        if self.viewerMode == ViewerMode.ImageViewerMode:
            self.viewer.on_mouse_motion(x, y, dx, dy)

    def on_mouse_scroll(self, x, y, scroll_x, scroll_y):
        if self.viewerMode == ViewerMode.ImageViewerMode:
            self.viewer.on_mouse_scroll(x, y, scroll_x, scroll_y)
        else:
            self.fileBrowser.on_mouse_scroll(x, y, scroll_x, scroll_y)

    def on_mouse_press(self, x, y, button, modifiers):
        if self.viewerMode == ViewerMode.ImageViewerMode:
            self.viewer.on_mouse_press(x, y, button, modifiers)
        else:
            self.fileBrowser.on_mouse_press(x, y, button, modifiers)

    def on_mouse_release(self, x, y, button, modifiers):
        if self.viewerMode == ViewerMode.ImageViewerMode:
            self.viewer.on_mouse_release(x, y, button, modifiers)

    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        if self.viewerMode == ViewerMode.ImageViewerMode:
            self.viewer.on_mouse_drag(x, y, dx, dy, buttons, modifiers)

