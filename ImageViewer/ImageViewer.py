import sys
import logging
from pathlib import Path

import pyglet

from ImageViewer.Viewer import Viewer
from ImageViewer.FileBrowser import FileBrowser
from ImageViewer.FileTypes import supportedExtensions
from ImageViewer.Logger import Logger

class ImageViewer:
    def __init__(self, fullScreenAllowed: bool) -> None:
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
                startInViewer = True
            else:
                # If it's not and image file, start the file browser in the parent of this file
                imagePath = imagePath.parent
                startInViewer = False
        else:
            # If it's a folder start in the browser in this folder
            startInViewer = False

        # Control whether the windows are allowed to be full screen
        self.fullScreenAllowed = fullScreenAllowed

        # Create a viewer
        self.viewer = Viewer(logQueue, self.fullScreenAllowed)

        # Create a file browser
        self.fileBrowser = FileBrowser(imagePath, self.viewer, self.viewer.SetupImagePathAndLoadImage, logQueue, self.fullScreenAllowed)

        # Let the viewer have access to the file browser
        self.viewer.fileBrowser = self.fileBrowser

        if startInViewer:
            # If we're starting in the viewer load the image
            self.viewer.SetupImagePathAndLoadImage(imagePath)

            # Hide the browser
            self.fileBrowser.set_visible(False)

            # Set the viewer to visible
            self.viewer.set_visible(True)

            # Activate the viewer window
            self.viewer.activate()
        else:
            # Hide the viewer
            self.viewer.set_visible(False)

            # Show the file browser
            self.fileBrowser.set_visible(True)

            # Activate the file browser
            self.fileBrowser.activate()

        # Log that the main loop is starting
        logQueue.put_nowait(('Starting Pyglet mainloop', logging.DEBUG))

        # Run the app
        pyglet.app.run()

        # Put None onto the thumbnail server queue to stop the process
        self.fileBrowser.thumbnailServer.childConn.send((None, None))

        # Log that the application is closing
        logQueue.put_nowait(('Exiting', logging.INFO))
