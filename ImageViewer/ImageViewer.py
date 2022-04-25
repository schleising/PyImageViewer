import sys
from pathlib import Path
from typing import Optional

import pyglet
from pyglet.window import key, event
from pyglet.image import ImageData

class ImageViewer(pyglet.window.Window):
    def __init__(self, argv: list[str]) -> None:
        # Call base class init
        super(ImageViewer, self).__init__()

        # Add an event logger
        # event_logger = event.WindowEventLogger()
        # self.push_handlers(event_logger)

        # State that there is not yet an image
        self.image: Optional[ImageData] = None

        # Set safe defaults
        self.xPos = 0
        self.yPos = 0
        self.currentImageWidth = 0
        self.currentImageHeight = 0

        # Check for a file on the command line
        if len(argv) > 1:
            # Get the file path
            filePath = Path(argv[1])

            # Get the parent folder
            imagePath = filePath.parent

            # Get the list of image files in this folder
            self.images = self._GetImagePathList(imagePath)

            # Work out where in the list the current image is
            self.currentImageIndex = self.images.index(filePath)
        else:
            # Use a default path
            imagePath = Path('/Users/steve/Pictures/Test Images')

            # Get the images
            self.images = self._GetImagePathList(imagePath)

            # Set the index to 0
            self.currentImageIndex = 0

        # Set the maximum image index
        self.maxImageIndex = len(self.images) - 1

        # Get the screen width and height
        self.screenWidth = pyglet.canvas.Display().get_default_screen().width
        self.screenHeight = pyglet.canvas.Display().get_default_screen().height

        # Set window to full screen
        self.set_fullscreen(True)

        # Load the image
        self._LoadImage()

        # Run the app
        pyglet.app.run()

    # Function to return a list of Paths pointing at images in the current folder
    def _GetImagePathList(self, imagePath: Path) -> list[Path]:
        # List of supported extensions
        extensions = [
            '.jpg',
            '.jpeg',
            '.png',
            '.gif',
            '.bmp',
            '.dds',
            '.exif',
            '.jp2',
            '.jpx',
            '.pcx',
            '.pnm',
            '.ras',
            '.tga',
            '.tif',
            '.tiff',
            '.xbm',
            '.xpm',
        ]

        # Return the list of images Paths
        return [image for image in imagePath.iterdir() if image.suffix.lower() in extensions]

    def _LoadImage(self) -> None:
        # Load the new image
        self.image = pyglet.image.load(self.images[self.currentImageIndex])

        # If either the image width or height is larger than the screen
        if self.image.width > self.screenWidth or self.image.height > self.screenHeight:
            # Squeeze the height and width
            self.currentImageWidth = min(self.image.width, self.screenWidth)
            self.currentImageHeight = min(self.image.height, self.screenHeight)

            # Work out whether the height or width has been squeezed the most
            if self.currentImageWidth / self.image.width < self.currentImageHeight / self.image.height:
                # Width squeezed most, so squeeze the height to maintain aspect ratio
                self.currentImageHeight = self.currentImageHeight * (self.currentImageWidth / self.image.width)
            elif self.currentImageHeight / self.image.height < self.currentImageWidth / self.image.width:
                # Height squeezed most, so squeeze the width to maintain aspect ratio
                self.currentImageWidth = self.currentImageWidth * (self.currentImageHeight / self.image.height)
        # If the image width and height are smaller than the screen, stretch the image to fit the screen
        elif self.image.width < self.screenWidth and self.image.height < self.screenHeight:
            # Set the image height and width to match the screen dimensions
            self.currentImageHeight = self.screenHeight
            self.currentImageWidth = self.screenWidth

            # Work out whether the height or width has been stretched the least
            if self.currentImageWidth / self.image.width < self.currentImageHeight / self.image.height:
                # Width stretched least, so stretch the height to maintain aspect ratio
                self.currentImageHeight = self.image.height * (self.currentImageWidth / self.image.width)
            elif self.currentImageHeight / self.image.height < self.currentImageWidth / self.image.width:
                # Height stretched least, so stretch the width to maintain aspect ratio
                self.currentImageWidth = self.image.width * (self.currentImageHeight / self.image.height)
        else:
            # Image dimensions exactly match the screen dimensions, so do nothing
            self.currentImageWidth = self.image.width
            self.currentImageHeight = self.image.height

        # Calculate the x and y position needed to draw the image in the centre of the screen
        self.xPos = self.screenWidth / 2 - self.currentImageWidth / 2
        self.yPos = self.screenHeight / 2 - self.currentImageHeight / 2

    def on_draw(self):
        # Check that image is not None
        if self.image:
            # Clear the existing screen
            self.clear()

            # Draw the new image
            self.image.blit(self.xPos, self.yPos, width=self.currentImageWidth, height=self.currentImageHeight)

    def on_key_press(self, symbol, modifiers):
        if symbol == key.RIGHT:
            # Increment the image index
            self.currentImageIndex += 1

            # Check that the new index is in bounds
            if self.currentImageIndex > self.maxImageIndex:
                # Reset to 0 if not
                self.currentImageIndex = 0
        elif symbol == key.LEFT:
            # Decrement the image index
            self.currentImageIndex -= 1

            # Check that the new index is in bounds
            if self.currentImageIndex < 0:
                # Set to the max index value if not
                self.currentImageIndex = self.maxImageIndex
        elif symbol == key.ESCAPE:
            # Quit the application
            pyglet.app.exit()

        # Load the new image
        self._LoadImage()

    def on_mouse_scroll(self, x, y, scroll_x, scroll_y):
        if self.image:
            if scroll_y > 0.2 or scroll_y < -0.2:
                # Scale the scroll value
                # scaleFactor = scroll_x / max(self.image.height, self.image.width)
                scaleFactor = 1.1 if scroll_y > 0 else 1 / 1.1
                print(scaleFactor)

                # Scale the width and height
                self.currentImageHeight = self.currentImageHeight * scaleFactor
                self.currentImageWidth = self.currentImageWidth * scaleFactor

            # Calculate the x and y position needed to draw the image in the centre of the screen
            self.xPos = self.screenWidth / 2 - self.currentImageWidth / 2
            self.yPos = self.screenHeight / 2 - self.currentImageHeight / 2

if __name__ == '__main__':
    imageViewer = ImageViewer(sys.argv)
