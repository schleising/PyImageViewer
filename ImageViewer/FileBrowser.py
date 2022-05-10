import logging
from pathlib import Path
from time import sleep
from typing import Callable, Optional
from multiprocessing import Process, Pipe, Lock
from multiprocessing.connection import Connection
import asyncio

from threading import Thread

import pyglet
from pyglet.window import key, Window, FPSDisplay
from pyglet.sprite import Sprite
from pyglet.graphics import Batch
from pyglet.image import load, ImageData
from pyglet.shapes import Line
from pyglet.text import Label

from PIL.Image import Image

from ImageViewer.FileTypes import supportedExtensions
from ImageViewer.ThumbnailServer import ThumbnailServer

class Container():
    # Load the default image
    defaultImage: ImageData = load(Path('ImageViewer/Resources/1x1_#000000ff.png'))

    def __init__(self, x: int, y: int, screenHeight: int, batch: Batch, childConn: Connection, lock):
        # The path this thumbnail represents
        self._path: Path = Path()

        # The size of the container
        self.containerSize: int = 0

        # Set the path of the folder image
        self.folderPath = Path('ImageViewer/Resources/285658_blue_folder_icon.png')

        # Sprite in this container
        self.sprite = Sprite(self.defaultImage, batch=batch)

        # Margin around thumbnails
        self.marginPix = 20

        # x position
        self._x = x

        # y position
        self._y = y

        # Set the screen height
        self.screenHeight = screenHeight

        # Check whether the image has been loaded
        self.imageLoaded = False

        # Request Queue
        self.childConn = childConn

        # Set the lock
        self.lock = lock

    def ReceiveImage(self, fullImage: Image) -> None:
        mode = fullImage.mode
        formatLength = len(mode) if mode else 4
        rawImage = fullImage.tobytes()
        self.sprite.image = ImageData(fullImage.width, fullImage.height, mode, rawImage, -fullImage.width * formatLength)
        # fullImage.show()

        # Work out the image size (thumbnail minus margin top, bottom, left and right)
        imageSize = self.containerSize - (self.marginPix * 2)

        # Scale the image to fit within the image size
        # self.sprite.scale = min(imageSize / self.sprite.image.width, imageSize / self.sprite.image.height)

        # Work out how far we have to shift the image to centre it in the thumbnail space
        xShift = (imageSize - self.sprite.width) // 2
        yShift = (imageSize - self.sprite.height) // 2

        # Calculate the resulting x and y of the bottom left of the image
        self.sprite.x = self.x + self.marginPix + xShift
        self.sprite.y = self.y + self.marginPix + yShift
        self.Running = False
        # sleep(1 / 50)

    def visible(self) -> bool:
        # Returns True if any part of the sprite is on screen
        return (self._y >= 0 and self._y < self.screenHeight) or (self._y + self.containerSize >= 0 and self._y + self.containerSize < self.screenHeight)

    def InSprite(self, x: int, y: int) -> bool:
        # Return true if the click was inside the image (not container) bounds
        return x >= self.sprite.x and y >= self.sprite.y and x <= self.sprite.x + self.sprite.width and y <= self.sprite.y + self.sprite.height

    @property
    def path(self) -> Path:
        return self._path

    @path.setter
    def path(self, path: Path) -> None:
        self._path = path
        self._updateSprite()

    def _updateSprite(self) -> None:
        if self.visible():
            if not self.imageLoaded:
                # Show that the image has been loaded
                self.imageLoaded = True

                if self._path.is_dir():
                    path = self.folderPath
                else:
                    path = self._path

                # Create a process to receive the loaded images
                # self.imageProcess = Thread(target=self.ReceiveImage, args=(self,))
                self.Running = True
                # self.imageProcess.start()

                # Work out the image size (thumbnail minus margin top, bottom, left and right)
                imageSize = self.containerSize - (self.marginPix * 2)

                self.lock.acquire()
                self.childConn.send((path, self._path, imageSize))
                self.lock.release()

        # else:
        #     if self.imageLoaded:
        #         self.sprite.image = self.defaultImage
        #         self.imageLoaded = False

    @property
    def x(self) -> int:
        return self._x

    @x.setter
    def x(self, x: int) -> None:
        self.sprite.x += x - self._x
        self._x = x
        # self._updateSprite()

    @property
    def y(self) -> int:
        return self._y

    @y.setter
    def y(self, y: int) -> None:
        self.sprite.y += y - self._y
        self._y = y
        self._updateSprite()

    def delete(self) -> None:
        self.sprite.delete()

class FileBrowser(Window):
    def __init__(self, inputPath: Path, viewerWindow: Window, loadFunction: Callable[[Path], None]) -> None:
        # Call base class init
        super(FileBrowser, self).__init__()

        # Set the viewer window so that we can control it before closing this one
        self.viewerWindow = viewerWindow

        # Set the load function so we can lod the newly chosen image in the viewer
        self.loadFunction: Callable[[Path], None] = loadFunction

        # Indicate whether the image viewer has been initialised
        self.imageViewerInitialised = False

        # Set the path of the input, getting the parent folder if this is actually a file
        self.inputPath = inputPath.parent if inputPath.is_file() else inputPath

        # Get the screen width and height
        self.set_fullscreen(True)

        # Create the thumbnail server and get the request queue
        self.thumbnailServer = ThumbnailServer()
        self.childConn = self.thumbnailServer.childConn
        self.pipeLock = Lock()

        # Controls for vertical scrolling to ensure the scroll remains in bounds
        self.scrollableAmount = 0
        self.currentScroll = 0

        # Margin around thumbnails
        self.marginPix = 20

        # Labels for folder names
        self.folderNames: list[Label] = []

        # Set to True to draw gridlines to help layout
        self.drawGridLines = True

        # The layout gridlines
        self.gridLines: list[Line] = []

        # Log that the browser has opened
        logging.info('Opened FileBrowser')

        # Controld for drawing the FPS
        self.displayFps = False
        self.fpsDisplay = FPSDisplay(self)

        # The batch to insert the sprites
        self.batch = Batch()

        # Constant defining the number of thnumbnails in a row
        self.thumbnailsPerRow = 6

        # The list of thumbnails
        self.thumbnailList: dict[Path, Container] = {}

        # Start a timed operation to receive images
        pyglet.clock.schedule_interval(self.ReceiveImages, 1 / 100)

        # Read the files and folders in this folder and create thumbnails from them
        self._GetThumbnails()

    def _GetThumbnails(self) -> None:
        # Initalise empty folder and file lists
        folderList: list[Path] = []
        fileList: list[Path] = []

        # Reset the scrolling
        self.currentScroll = 0

        # Clear the thumbnails down if they exist
        if self.thumbnailList:
            for thumbnail in self.thumbnailList.values():
                thumbnail.delete()
            self.thumbnailList.clear()

        # Clear the gridlines down if they exits
        if self.gridLines:
            for gridLine in self.gridLines:
                gridLine.delete()
            self.gridLines.clear()

        # Clear the folder names down if they exist
        if self.folderNames:
            for folderName in self.folderNames:
                folderName.delete()
            self.folderNames.clear()

        # Work out the full thumbnail size (this is the size reserved for image and name)
        thumbnailSize = self.width / self.thumbnailsPerRow

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
            yStart = self.height - (thumbnailSize * ((count // self.thumbnailsPerRow) + 1))

            # Create a sprite from the image and add it to the drawing batch
            container = Container(xStart, yStart, self.height, self.batch, self.childConn, self.pipeLock)

            # Tell the sprite how big the container is
            container.containerSize = thumbnailSize

            # Add the path of the image or folder
            container.path = path

            # Append the sprite to the list
            self.thumbnailList[path] = container

            # Work out how much we are allowed to scroll this view vertically
            self.scrollableAmount = abs(container.y) if container.y < 0 else 0

            if self.drawGridLines:
                # If we are drawing gridlines, add them to the gridline list
                self.gridLines.append(Line(xStart, yStart, xStart, yStart + thumbnailSize, batch=self.batch))
                self.gridLines.append(Line(xStart, yStart + thumbnailSize, xStart + thumbnailSize, yStart + thumbnailSize, batch=self.batch))
                self.gridLines.append(Line(xStart + thumbnailSize, yStart + thumbnailSize, xStart + thumbnailSize, yStart, batch=self.batch))
                self.gridLines.append(Line(xStart + thumbnailSize, yStart, xStart, yStart, batch=self.batch))

            # If this is a folder, add the name
            if path.is_dir():
                # Work out the centre x and y of the folder name
                xlabel = xStart + (thumbnailSize / 2)
                ylabel = yStart + (self.marginPix / 2)

                # Create the label using the centre anchor position
                label = Label(path.name, x=xlabel, y=ylabel, anchor_x='center', anchor_y='center', batch=self.batch)

                # Append the label to the list
                self.folderNames.append(label)

    def on_key_press(self, symbol, modifiers):
        if symbol == key.ESCAPE:
            # Log that the browser window is closing
            logging.info('Closing File Browser')

            if self.imageViewerInitialised:
                # Set the viewer window back to full screen
                self.viewerWindow.set_fullscreen(True)

                # Activate the viewer window to ensure it has focus
                self.viewerWindow.activate()

                # Show the viewer windoes
                self.viewerWindow.set_visible(True)

                # Hide this browser window
                self.set_visible(False)
            else:
                # If the viewer was never initialised, exit the application
                pyglet.app.exit()
        elif symbol == key.F:
            # Toggle display of the FPS
            self.displayFps = not self.displayFps

    def ReceiveImages(self, dt) -> None:
        # print('Rec')
        while self.childConn.poll():
            self.pipeLock.acquire()
            path, fullImage = self.childConn.recv()
            self.pipeLock.release()

            if path in self.thumbnailList:
                self.thumbnailList[path].ReceiveImage(fullImage)

    def on_draw(self):
        # self.ReceiveImages()

        # Clear the display
        self.clear()

        # Draw the sprites
        self.batch.draw()

        # Display the FPS if enabled
        if self.displayFps:
            self.fpsDisplay.draw()

    def on_mouse_scroll(self, x, y, scroll_x, scroll_y):
        # Check that there has been enough of a scroll to be worth registering
        if scroll_y < -0.2:
            scroll = scroll_y * 10
        elif scroll_y > 0.2:
            scroll = scroll_y * 10
        else:
            scroll = None

        if scroll:
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

            # asyncio.run(self.scrollThumbnails(scroll))
            for thumbail in self.thumbnailList.values():
                thumbail.y += scroll

            # Move the gridlines
            for gridLine in self.gridLines:
                gridLine.y += scroll
                gridLine.y2 += scroll

            # Move the folder names
            for folderName in self.folderNames:
                folderName.y += scroll

    def on_mouse_press(self, x, y, button, modifiers):
        # Iterate through the sprites
        for sprite in self.thumbnailList.values():
            # Get each sprite to check whether it was the target of the mouse click
            if sprite.InSprite(x, y):
                if sprite.path:
                    if sprite.path.is_file():
                        # If this is a file, log that the browser window will close
                        logging.info('Closing File Browser due to click')

                        # Set the viewer back to full screen
                        self.viewerWindow.set_fullscreen(True)

                        # Show the viewer window
                        self.viewerWindow.set_visible(True)

                        # Load the new image in the viewer window
                        self.loadFunction(sprite.path)

                        # Hide this window
                        self.set_visible(False)

                        # Activate teh viewer window
                        self.viewerWindow.activate()

                        # Exit the loop
                        break
                    else:
                        # If this is a folder, update the path with the new folder path
                        self.inputPath = sprite.path

                        # Regenerate the thumbnails for the new folder
                        self._GetThumbnails()

                        # Exit the loop
                        break
