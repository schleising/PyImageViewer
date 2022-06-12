from enum import Enum, auto
import sys
import logging
from pathlib import Path

import pyglet
from pyglet.window import key, FPSDisplay

from ImageViewer.ImageViewer import ImageViewer
from ImageViewer.FileBrowser import FileBrowser
from ImageViewer.FileTypes import supportedExtensions
from ImageViewer.Logger import Logger

class ViewerMode(Enum):
    FileBrowserMode = auto()
    ImageViewerMode = auto()

class MainWindow(pyglet.window.Window):
    def __init__(self, debugMode: bool) -> None:
        # Call base class init
        super(MainWindow, self).__init__(resizable=True, width=1280, height=720, style=pyglet.window.Window.WINDOW_STYLE_BORDERLESS)

        # Add an event logger
        if debugMode:
            from pyglet.window import event
            event_logger = event.WindowEventLogger()
            self.push_handlers(event_logger)
            logLevel = logging.DEBUG
        else:
            logLevel = logging.INFO

        # Create a logger instance
        logger = Logger(logLevel)

        # Get the logger queue
        self.logQueue = logger.messageQueue

        # Log that the application has started
        self.logQueue.put_nowait(('Application Started', logging.INFO))

        # Control whether the FPS value is displayed
        self.displayFps = False
        self.fpsDisplay = FPSDisplay(self)

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

        # Set window to full screen
        self.maximize()

        # Create a viewer
        self.viewer = ImageViewer(self, self.logQueue)

        # Create a file browser
        self.fileBrowser = FileBrowser(imagePath, self, self.viewer.SetupImagePathAndLoadImage, self.logQueue)

        # Let the viewer have access to the file browser
        self.viewer.fileBrowser = self.fileBrowser

        if self.viewerMode == ViewerMode.ImageViewerMode:
            # If we're starting in the viewer load the image
            self.viewer.SetupImagePathAndLoadImage(imagePath)

        # Log that the main loop is starting
        self.logQueue.put_nowait(('Starting Pyglet mainloop', logging.DEBUG))

        # Run the app
        pyglet.app.run()

        # Put None onto the thumbnail server queue to stop the process
        self.fileBrowser.thumbnailServer.toTS.put_nowait((None, None))

        # Log that the application is closing
        self.logQueue.put_nowait(('Exiting', logging.INFO))

    def toggleViewer(self) -> None:
        if self.viewerMode == ViewerMode.FileBrowserMode:
            self.viewerMode = ViewerMode.ImageViewerMode
        else:
            self.viewerMode = ViewerMode.FileBrowserMode

    def on_draw(self):
        # Clear the window
        self.clear()

        if self.viewerMode == ViewerMode.ImageViewerMode:
            # If in viewer mode draw the single image
            self.viewer.on_draw()
        else:
            # If in file browser move, draw the thumbnail containers
            self.fileBrowser.on_draw()

        # Draw the frames per second if enabled
        if self.displayFps:
            self.fpsDisplay.draw()

    def on_key_press(self, symbol, modifiers):
        if symbol == key.ESCAPE:
            # Quit the application
            self.logQueue.put_nowait(('ESC Pressed, Exiting Pyglet application', logging.DEBUG))
            pyglet.app.exit()
        elif symbol == key.F:
            self.displayFps = not self.displayFps
            return
        elif self.viewerMode == ViewerMode.ImageViewerMode:
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
