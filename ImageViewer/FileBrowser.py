import logging
from pathlib import Path
import threading
import queue
from typing import Callable, Optional

import pyglet
from pyglet.window import key, mouse, Window
from pyglet.graphics import Batch
from pyglet.image import ImageData

from ImageViewer.FileTypes import supportedExtensions
from ImageViewer.ThumbnailServer import ThumbnailServer
from ImageViewer.Container import Container
# from ImageViewer.ImageViewer import ImageViewer

class FileBrowser():
    def __init__(self, inputPath: Path, mainWindow: Window, loadFunction: Callable[[Path], None], logQueue: queue.Queue) -> None:

        # Set the main window
        self.mainWindow = mainWindow

        # Set the log queue
        self.logQueue = logQueue

        # Set the load function so we can lod the newly chosen image in the viewer
        self.loadFunction: Callable[[Path], None] = loadFunction

        # Indicate whether the image viewer has been initialised
        self.imageViewerInitialised = False

        # Set the path of the input, getting the parent folder if this is actually a file
        self.inputPath = inputPath.parent if inputPath.is_file() else inputPath

        # Create and start the thumbnail server and get the request queue and lock
        self.thumbnailServer = ThumbnailServer(self.logQueue)
        self.thumbnailServer.start()

        # Get the queue to send data to the Thumbnail Server
        self.toTS = self.thumbnailServer.toTS

        # Get the queue to receive data from the Thumbnail Server
        self.fromTS = self.thumbnailServer.fromTS

        # Lock access to the queue such that only one thread reads at a time
        self.queueLock = threading.Lock()

        # Controls for vertical scrolling to ensure the scroll remains in bounds
        self.scrollableAmount = 0
        self.currentScroll = 0

        # Margin around thumbnails
        self.marginPix = 20

        # Log that the browser has opened
        self.logQueue.put_nowait(('Opened FileBrowser', logging.DEBUG))

        # The batch to insert the sprites
        self.batch = Batch()

        # Constant defining the number of thnumbnails in a row
        self.thumbnailsPerRow = 8

        # The dict of thumbnails indexed by Path
        self.thumbnailDict: dict[Path, Container] = {}

        # Store the index of the image which is highlighted
        self.highlightedImageIndex = 0

        # Read the files and folders in this folder and create thumbnails from them
        self._GetThumbnails()

    def _GetThumbnails(self) -> None:
        # Reset the highlighted index to 0
        self.highlightedImageIndex = 0

        # Initalise empty folder and file lists
        folderList: list[Path] = []
        fileList: list[Path] = []

        # Reset the scrolling
        self.currentScroll = 0

        # Clear the thumbnails down if they exist
        if self.thumbnailDict:
            for thumbnail in self.thumbnailDict.values():
                thumbnail.delete()
            self.thumbnailDict.clear()

        # Work out the full thumbnail size (this is the size reserved for image and name)
        thumbnailSize = self.mainWindow.width // self.thumbnailsPerRow

        # Tell the sprite how big the container is
        Container.setContainerSize(thumbnailSize)

        # Iterate through the files in the folder
        for path in self.inputPath.iterdir():
            # Ignore files starting with a . as they are hidden
            if not path.name.startswith('.'):
                if path.is_dir():
                    # If this is a folder append it to the folder list
                    folderList.append(path)
                elif path.suffix.lower() in supportedExtensions.values():
                    # If this is a file, append it to the file list
                    fileList.append(path)

        # Sort the folder list and insert the parent of this folder at the start
        folderList = list(sorted(folderList, key=lambda path: path.name.lower()))
        folderList.insert(0, self.inputPath.parent)

        # Sort the file list
        fileList = list(sorted(fileList, key=lambda path: path.name.lower()))

        # The full list is now folders followed by files
        fullPathList = folderList + fileList

        # Iterate over the full list of paths
        for count, path in enumerate(fullPathList):
            # Get the x and y of the thumbnail space
            xStart = thumbnailSize * (count % self.thumbnailsPerRow)
            yStart = self.mainWindow.height - (thumbnailSize * ((count // self.thumbnailsPerRow) + 1))

            # Create a sprite from the image and add it to the drawing batch
            container = Container(xStart, yStart, self.mainWindow.height, self.batch, self.toTS, self.queueLock)

            # Add the path of the image or folder, this property will call _updateSprite triggering the thumbnail server to fetch the image
            container.path = path

            # Schedule a check for images from the thumbnail server
            pyglet.clock.schedule_once(self.ReceiveImages, 1 / 60)

            # Add the sprite to the dictionary
            self.thumbnailDict[path] = container

            # Work out how much we are allowed to scroll this view vertically
            self.scrollableAmount = abs(container.y) if container.y < 0 else 0

        # Highlight the first thumbnail
        list(self.thumbnailDict.values())[self.highlightedImageIndex].highlighted = True

    def ReceiveImages(self, dt) -> None:
        # Assume that the queue is not empty
        queueEmpty = False

        # Receive all the images we can from the thumbnail server if any are available
        while not queueEmpty:
            # Receive the image, getting a lock to ensure this end of the pipe is accessed by only one thread
            with self.queueLock:
                try:
                    path, fullImage = self.fromTS.get_nowait()
                except queue.Empty:
                    # Show that the queue is now empty
                    queueEmpty = True

                    # Initialise path and fullImage to None
                    path: Optional[str] = None
                    fullImage: Optional[ImageData] = None

            # If the path is in the dictionary, call the container's ReceiveImage function
            if path is not None and fullImage is not None and path in self.thumbnailDict:
                self.thumbnailDict[path].ReceiveImage(fullImage)

        # Check if any containers are waiting for images
        if any([container.imageLoading for container in self.thumbnailDict.values()]):
            # Schedule a check for images from the thumbnail server
            pyglet.clock.schedule_once(self.ReceiveImages, 1 / 60)

    def on_key_press(self, symbol, modifiers):
        if symbol == key.ESCAPE:
            # Log that the browser window is closing
            self.logQueue.put_nowait(('Closing File Browser', logging.DEBUG))

            # Exit the application
            pyglet.app.exit()

        elif symbol == key.UP:
            if modifiers & key.MOD_SHIFT:
                # Update the path with the parent folder path
                self.inputPath = self.inputPath.parent

                # Regenerate the thumbnails for the new folder
                self._GetThumbnails()
            else:
                # Reset the highlight on the current thumbnail
                list(self.thumbnailDict.values())[self.highlightedImageIndex].highlighted = False

                # Increment the highlighted index
                self.highlightedImageIndex -= self.thumbnailsPerRow

                # Check the index is in bounds
                if self.highlightedImageIndex < 0:
                    self.highlightedImageIndex = 0

                # Get the new thumbnail
                newThumbnail = list(self.thumbnailDict.values())[self.highlightedImageIndex]

                # Highlight the image at the new index
                newThumbnail.highlighted = True

                # Scroll the display if necesary
                self.CheckThumbnailVisible(newThumbnail)
        elif symbol == key.DOWN:
            # Reset the highlight on the current thumbnail
            list(self.thumbnailDict.values())[self.highlightedImageIndex].highlighted = False

            # Increment the highlighted index
            self.highlightedImageIndex += self.thumbnailsPerRow

            # Check the index is in bounds
            if self.highlightedImageIndex >= len(self.thumbnailDict):
                self.highlightedImageIndex = len(self.thumbnailDict) - 1

            # Get the new thumbnail
            newThumbnail = list(self.thumbnailDict.values())[self.highlightedImageIndex]

            # Highlight the image at the new index
            newThumbnail.highlighted = True

            # Scroll the display if necesary
            self.CheckThumbnailVisible(newThumbnail)
        elif symbol == key.RIGHT:
            # Reset the highlight on the current thumbnail
            list(self.thumbnailDict.values())[self.highlightedImageIndex].highlighted = False

            # Increment the highlighted index
            self.highlightedImageIndex += 1

            # Check the index is in bounds
            if self.highlightedImageIndex >= len(self.thumbnailDict):
                self.highlightedImageIndex = 0

            # Get the new thumbnail
            newThumbnail = list(self.thumbnailDict.values())[self.highlightedImageIndex]

            # Highlight the image at the new index
            newThumbnail.highlighted = True

            # Scroll the display if necesary
            self.CheckThumbnailVisible(newThumbnail)
        elif symbol == key.LEFT:
            # Reset the highlight on the current thumbnail
            list(self.thumbnailDict.values())[self.highlightedImageIndex].highlighted = False

            # Decrement the highlighted index
            self.highlightedImageIndex -= 1

            # Check the index is in bounds
            if self.highlightedImageIndex < 0:
                self.highlightedImageIndex = len(self.thumbnailDict) - 1

            # Get the new thumbnail
            newThumbnail = list(self.thumbnailDict.values())[self.highlightedImageIndex]

            # Highlight the image at the new index
            newThumbnail.highlighted = True

            # Scroll the display if necesary
            self.CheckThumbnailVisible(newThumbnail)
        elif symbol == key.ENTER:
            # Load the currently highlighted image or folder
            self.LoadImage(list(self.thumbnailDict.values())[self.highlightedImageIndex].path)
        # elif symbol == key.F:
        #     # Toggle display of the FPS
        #     self.displayFps = not self.displayFps
        elif symbol == key.G:
            for thumbnail in self.thumbnailDict.values():
                # Toggle display of gridlines
                thumbnail.drawGridLines = not thumbnail.drawGridLines

    def CheckThumbnailVisible(self, newThumbnail: Container) -> None:
        # Check whether the thumbnail is fully on the screen
        if newThumbnail.y < 0:
            # If it is off the bottom, work out the scroll amount
            scrollAmount = abs(newThumbnail.y)

            # Scroll by this amount
            self.ScrollBrowser(scrollAmount)
        elif newThumbnail.y + newThumbnail.containerSize > self.mainWindow.height:
            # If it is off the top, work out the scroll amount
            scrollAmount = self.mainWindow.height - (newThumbnail.y + newThumbnail.containerSize)

            # Scroll by this amount
            self.ScrollBrowser(scrollAmount)

    def on_draw(self):
        # Clear the display
        self.mainWindow.clear()

        # Draw the sprites
        self.batch.draw()

    def on_mouse_scroll(self, x, y, scroll_x, scroll_y):
        # Check that there has been enough of a scroll to be worth registering
        if scroll_y < -0.2:
            scroll = scroll_y * 10
        elif scroll_y > 0.2:
            scroll = scroll_y * 10
        else:
            scroll = None

        if scroll:
            # Scroll by the scroll amount
            self.ScrollBrowser(scroll)

    def ScrollBrowser(self, scroll) -> None:
        # Work out what the new scroll value would be
        newScroll = self.currentScroll + scroll

        # Check that this scroll value wouldn't take the view out of bounds, if so, constrain it
        if newScroll < self.scrollableAmount and newScroll >= 0:
            self.currentScroll = newScroll
        elif newScroll < 0:
            scroll = -self.currentScroll
            self.currentScroll = 0
        else:
            scroll = self.scrollableAmount - self.currentScroll
            self.currentScroll = self.scrollableAmount

        # Update all the thumbnails, this will trigger new images to be loaded bythe thumbnail server if necessary
        for thumbail in self.thumbnailDict.values():
            thumbail.y += scroll

        # Schedule a check for images from the thumbnail server
        pyglet.clock.schedule_once(self.ReceiveImages, 1 / 60)

    def on_mouse_press(self, x, y, button, modifiers):
        if button == mouse.LEFT:
            # Iterate through the sprites
            for sprite in self.thumbnailDict.values():
                # Get each sprite to check whether it was the target of the mouse click
                if sprite.InSprite(x, y):
                    if sprite.path:
                        # Load the new image
                        self.LoadImage(sprite.path)

                        # Exit the loop
                        break
        elif button == mouse.RIGHT:
            # Log that the browser window is closing
            self.logQueue.put_nowait(('Closing File Browser', logging.DEBUG))

            # Exit the application
            pyglet.app.exit()

    def LoadImage(self, imagePath: Path) -> None:
        if imagePath.is_file():
            # If this is a file, log that the browser window will close
            self.logQueue.put_nowait(('Closing File Browser due to click', logging.DEBUG))

            # Load the new image in the viewer window
            self.loadFunction(imagePath)

            # Set the viewer back to full screen
            self.mainWindow.toggleViewer()

        else:
            # If this is a folder, update the path with the new folder path
            self.inputPath = imagePath

            # Regenerate the thumbnails for the new folder
            self._GetThumbnails()

    def on_resize(self, width, height):
        # self.width = width
        # self.height = height
        pass
