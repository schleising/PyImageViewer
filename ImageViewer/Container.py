from pathlib import Path
import queue
from typing import Optional

from PIL import Image
from pyglet.sprite import Sprite
from pyglet.graphics import Batch
from pyglet.image import ImageData
from pyglet.shapes import Line
from pyglet.text import Label

class Container():
    # Load the default image
    thumbnailInputImage = Image.open(Path('ImageViewer/Resources/Loading Icon.png'))

    # Set the folder image
    folderInputImage = Image.open(Path('ImageViewer/Resources/285658_blue_folder_icon.png'))

    # The size of the container
    containerSize: int = 0

    # Margin around thumbnails
    marginPix = 20

    # Size of the image inside the container
    imageSize = 0

    # Set the sprite image to be None
    thumbnailImage = None

    # Set the folder image to None
    folderImage = None

    def __init__(self, x: int, y: int, screenHeight: int, batch: Batch, toTS: queue.Queue, lock):
        # The path this thumbnail represents
        self._path: Path = Path()

        # Set the batch
        self.batch = batch

        # Initially set the sprite to None
        self.sprite = None

        # x position
        self._x = x

        # y position
        self._y = y

        # Set the screen height
        self.screenHeight = screenHeight

        # Check whether the image has been loaded
        self.imageLoaded = False

        # Check whether we are loading an image
        self.imageLoading = False

        # Queue to send image load requests
        self.toTS = toTS

        # Lock for the pipe
        self.lock = lock

        # Label for this container
        self.label = None

        # Set to True to draw gridlines to help layout
        self._drawGridLines = False

        # The layout gridlines
        self.gridLines: list[Line] = []

        # Indicate whether this image is highlighted
        self._highlighted = False

    @classmethod
    def setContainerSize(cls, size: int) -> None:
        # If we have not yet created an image for the loading sprite
        if cls.thumbnailImage is None or cls.folderImage is None or cls.containerSize != size:
            # Set the container size
            cls.containerSize = size

            # Work out how big the thumbnail should be in the conainer
            cls.imageSize = cls.containerSize - (cls.marginPix * 2)

            # Create a thumbnail of the loading image
            cls.thumbnailInputImage.thumbnail((cls.imageSize, cls.imageSize))

            # Create a thumbnail of the folder image
            cls.folderInputImage.thumbnail((cls.imageSize, cls.imageSize))

            # Create the sprite for the thumbnail
            cls.thumbnailImage = cls.CreateThumbnailSprite(cls.thumbnailInputImage)

            # Create the sprite for the folder
            cls.folderImage = cls.CreateThumbnailSprite(cls.folderInputImage)

    @classmethod
    def CreateThumbnailSprite(cls, thumbnail: Image.Image) -> ImageData:
        # Get the mode (e.g., 'RGBA')
        mode = thumbnail.mode

        # Get the number of bytes per pixel
        formatLength = len(mode) if mode else 4

        # Convert the image to bytes
        rawImage = thumbnail.tobytes()

        # Create a Pyglet ImageData object from the bytes
        return ImageData(thumbnail.width, thumbnail.height, mode, rawImage, -thumbnail.width * formatLength)

    def InitialiseSprite(self) -> None:
        # Delete the sprite if it exists
        if self.sprite:
            self.sprite.delete()
            self.sprite = None

        # Check whther this is a file or folder and set the thumbnail appropriately
        if self._path.is_dir():
            # Set the sprite
            self.sprite = Sprite(self.folderImage, batch=self.batch)
        else:
            # Set the sprite
            self.sprite = Sprite(self.thumbnailImage, batch=self.batch)

            # Make the sprite mostly transparent for the loading image
            self.sprite.opacity = 64

        # Work out how far we have to shift the image to centre it in the thumbnail space
        xShift = (self.imageSize - self.sprite.width) // 2
        yShift = (self.imageSize - self.sprite.height) // 2

        # Calculate the resulting x and y of the bottom left of the image
        self.sprite.x = self.x + self.marginPix + xShift
        self.sprite.y = self.y + self.marginPix + yShift

        if self.label is None:
            # Work out the centre x and y of the label
            xlabel = self.x + (self.containerSize / 2)
            ylabel = self.y + (self.marginPix / 2)

            # Get the stem, only getting the first and last ten characters if the filename is longer than 23 characters
            labelText = self._path.stem if len(self._path.stem) <= 23 else f'{self._path.stem[:10]}...{self._path.stem[-10:]}'

            # Create the label using the centre anchor position
            self.label = Label(labelText, x=xlabel, y=ylabel, anchor_x='center', anchor_y='center', batch=self.batch)

        if not self.gridLines:
            # Add gridlines to the gridline list
            self.gridLines.append(Line(self.x, self.y, self.x, self.y + self.containerSize, batch=self.batch))
            self.gridLines.append(Line(self.x, self.y + self.containerSize, self.x + self.containerSize, self.y + self.containerSize, batch=self.batch))
            self.gridLines.append(Line(self.x + self.containerSize, self.y + self.containerSize, self.x + self.containerSize, self.y, batch=self.batch))
            self.gridLines.append(Line(self.x + self.containerSize, self.y, self.x, self.y, batch=self.batch))

            # Show or hide the gridlines
            for gridLine in self.gridLines:
                gridLine.visible = self._drawGridLines

    @property
    def drawGridLines(self) -> bool:
        return self._drawGridLines

    @drawGridLines.setter
    def drawGridLines(self, drawGridLines: bool) -> None:
        # Set the new value for Draw Grid Lines
        self._drawGridLines = drawGridLines

        # Show or hide the gridlines
        for gridLine in self.gridLines:
            gridLine.visible = self._drawGridLines

    @property
    def highlighted(self) -> bool:
        # Return the current value of highlighted
        return self._highlighted

    @highlighted.setter
    def highlighted(self, highlighted: bool) -> None:
        # Set the highlighted value
        self._highlighted = highlighted

        if self._highlighted:
            # If this thumbnail is highlighted, set the colour
            if self.sprite:
                self.sprite.color = (180, 180, 255)

            # Highlight the label dodger blue
            if self.label:
                self.label.color = (30, 144, 255, 255)
        else:
            # If this is not highlighted reset the colour
            if self.sprite:
                self.sprite.color = (255, 255, 255)

            # Reset the label highlight
            if self.label:
                self.label.color = (255, 255, 255, 255)

    def ReceiveImage(self, image: Optional[ImageData]) -> None:
        # We are no longer loading an image
        self.imageLoading = False

        # Check that the thumbnail has actually been loaded
        if image is not None and self.sprite is not None:
            # Set the sprites image to the one recieved from the thumbnail server process
            self.sprite.image = image

            # Reset the sprite opacity to 100%
            self.sprite.opacity = 255

            # Work out how far we have to shift the image to centre it in the thumbnail space
            xShift = (self.imageSize - self.sprite.width) // 2
            yShift = (self.imageSize - self.sprite.height) // 2

            # Calculate the resulting x and y of the bottom left of the image
            self.sprite.x = self.x + self.marginPix + xShift
            self.sprite.y = self.y + self.marginPix + yShift

    def visible(self) -> bool:
        # Returns True if any part of the sprite is on screen
        return (self._y >= 0 and self._y < self.screenHeight) or (self._y + self.containerSize >= 0 and self._y + self.containerSize < self.screenHeight)

    def InSprite(self, x: int, y: int) -> bool:
        # Return true if the click was inside the image (not container) bounds
        if self.sprite:
            return x >= self.sprite.x and y >= self.sprite.y and x <= self.sprite.x + self.sprite.width and y <= self.sprite.y + self.sprite.height
        else:
            return False

    @property
    def path(self) -> Path:
        return self._path

    @path.setter
    def path(self, path: Path) -> None:
        # Set the path
        self._path = path

        # Initialise the sprite now we know the path
        self.InitialiseSprite()

        # Trigger off the thumbnail server to get the thumbnail
        self._updateSprite()

    def _updateSprite(self) -> None:
        if self.visible():
            # Initialise the sprite if it doesn't already exist
            if self.sprite is None:
                self.InitialiseSprite()

            if not self.imageLoaded and not self._path.is_dir():
                # Show that the image has been loaded so we only request it once
                self.imageLoaded = True

                # Show that an image is being loaded so that a timer gets triggered to check for a response
                self.imageLoading = True

                # Send a request to load the image at path, self._path is sent to allow matching the image to the container map
                # A queue can only have one thread access a particular end, otherwise the data will be corrupt
                with self.lock:
                    self.toTS.put_nowait((self._path, self.imageSize))
        else:
            # Set the image loaded and image loading variables to False
            self.imageLoaded = False
            self.imageLoading = False

            # Clear the sorite, label and gridlines
            self.delete()

    @property
    def x(self) -> int:
        return self._x

    @x.setter
    def x(self, x: int) -> None:
        # Work out the scroll amount
        scroll = x - self._x

        # Move the sprite in x
        if self.sprite:
            self.sprite.x += scroll

        # Move the label in x
        if self.label:
            self.label.x += scroll

        # Move the gridlines
        for gridLine in self.gridLines:
            gridLine.x += scroll
            gridLine.x2 += scroll

        # Move the container in x
        self._x = x

        # Load the image if it is now visible and wasn't before
        self._updateSprite()

    @property
    def y(self) -> int:
        return self._y

    @y.setter
    def y(self, y: int) -> None:
        # Work out the scroll amount
        scroll = y - self._y

        # Move the sprite in y
        if self.sprite:
            self.sprite.y += scroll

        # Move the label in x
        if self.label:
            self.label.y += scroll

        # Move the gridlines
        for gridLine in self.gridLines:
            gridLine.y += scroll
            gridLine.y2 += scroll

        # Move the container in y
        self._y = y

        # Load the image if it is now visible and wasn't before
        self._updateSprite()

    def delete(self) -> None:
        # Delete the sprite
        if self.sprite:
            self.sprite.delete()
            self.sprite = None

        # Delete the label
        if self.label:
            self.label.delete()
            self.label = None

        # Clear the gridlines down if they exits
        if self.gridLines:
            for gridLine in self.gridLines:
                gridLine.delete()
                gridLine = None
            self.gridLines.clear()
