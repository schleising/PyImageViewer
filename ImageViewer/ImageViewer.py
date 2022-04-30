import sys
from pathlib import Path
from typing import Optional

import pyglet
from pyglet.window import key
from pyglet.sprite import Sprite
from pyglet.image import ImageData

class ImageViewer(pyglet.window.Window):
    def __init__(self, argv: list[str]) -> None:
        # Call base class init
        super(ImageViewer, self).__init__()

        # Add an event logger
        # event_logger = event.WindowEventLogger()
        # self.push_handlers(event_logger)

        # Sprite containing the image
        self.sprite: Optional[Sprite] = None

        # Set safe defaults
        self.xStartDrag = 0
        self.yStartDrag = 0
        self.rectangle = None

        # Setup ordered groups to ensure shapes are drawn on top of the image
        self.background = pyglet.graphics.OrderedGroup(0)
        self.foreground = pyglet.graphics.OrderedGroup(1)

        # Create a batch drawing context
        self.batch = pyglet.graphics.Batch()

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

        # Return the list of images Paths, sorted alphabetically (case insensitive)
        return sorted([image for image in imagePath.iterdir() if image.suffix.lower() in extensions], key=lambda x: x.name.lower())

    def HideMouse(self, dt: float = 0.0) -> None:
        # Hide the mouse after the timeout expires
        self.set_mouse_visible(False)

    def ShowMouse(self, autoHide: bool) -> None:
        # Unschedule the mouse hide callback
        pyglet.clock.unschedule(self.HideMouse)

        # Set the mouse to be visible
        self.set_mouse_visible(True)

        # If we want to hide the mouse again after a timeout, schedule the callback
        if autoHide:
            pyglet.clock.schedule_once(self.HideMouse, 0.5)

    def _LoadImage(self) -> None:
        # Remove the existing sprite if it exists
        if self.sprite:
            self.sprite.delete()
            self.sprite = None

        # Remove the existing rectangle if it exists
        if self.rectangle:
            self.rectangle.delete()
            self.rectangle = None

        # Load the new image
        image: ImageData = pyglet.image.load(self.images[self.currentImageIndex])

        # Work out how much to scale each axis to fit into the screen
        xScale = self.screenWidth / image.width
        yScale = self.screenHeight / image.height

        # Both axes need to be scaled by the smallest number
        scalingFactor = min(xScale, yScale)

        # Calculate the x and y position needed to draw the image in the centre of the screen
        xPos = self.screenWidth / 2 - (scalingFactor * image.width / 2)
        yPos = self.screenHeight / 2 - (scalingFactor * image.height / 2)

        # Create a sprite containing the image at the calculated x, y position
        self.sprite = pyglet.sprite.Sprite(img=image, x=xPos, y=yPos, batch=self.batch, group=self.background)

        # Scale the sprite
        self.sprite.scale = scalingFactor

        # Hide the mouse immediately
        self.HideMouse()

    def on_draw(self):
        # Check that image is not None
        if self.sprite:
            # Clear the existing screen
            self.clear()

            # Draw the batch
            self.batch.draw()

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
        else:
            # If this is not one of the above keys return without redrawing the image
            return

        # Clear the rectangle
        if self.rectangle:
            self.rectangle.delete()
            self.rectangle = None

        # Load the new image
        self._LoadImage()

    def on_mouse_motion(self, x, y, dx, dy):
        # Show the mouse when it moves, autohiding afterwards
        self.ShowMouse(True)

    def on_mouse_scroll(self, x, y, scroll_x, scroll_y):
        # Show the mouse when scrolling, autohiding afterwards
        self.ShowMouse(True)

        if self.sprite:
            if scroll_y > 0.2 or scroll_y < -0.2:
                # Scale the scroll value
                scaleFactor = 1.1 if scroll_y < 0 else 1 / 1.1

                # Work out how far the mouse is from the image bottom left
                xMouseImagePos = x - self.sprite.x
                yMouseImagePos = y - self.sprite.y

                # Scale this distance by the zoom factor
                xScaledMouseImagePos = xMouseImagePos * scaleFactor
                yScaledMouseImagePos = yMouseImagePos * scaleFactor

                # Work out the new x and y of the image bottom left keeping the image static at the mouse position
                self.sprite.x = self.sprite.x + xMouseImagePos - xScaledMouseImagePos
                self.sprite.y = self.sprite.y + yMouseImagePos - yScaledMouseImagePos

                # Rescale the sprite
                self.sprite.scale = self.sprite.scale * scaleFactor

        # Clear the rectangle
        if self.rectangle:
            self.rectangle.delete()
            self.rectangle = None

    def on_mouse_press(self, x, y, button, modifiers):
        # Show the mouse while pressed, do not autohide
        self.ShowMouse(False)

        # Clear the rectangle
        if self.rectangle:
            self.rectangle.delete()
            self.rectangle = None

        if modifiers & key.MOD_COMMAND:
            # Log the starting point of the drag
            self.xStartDrag = x
            self.yStartDrag = y

            # Get the crosshair cursor
            cursor = self.get_system_mouse_cursor(self.CURSOR_CROSSHAIR)
        else:
            # Get the hand cursor
            cursor = self.get_system_mouse_cursor(self.CURSOR_HAND)

        # Set the hand as the current cursor
        self.set_mouse_cursor(cursor)

    def on_mouse_release(self, x, y, button, modifiers):
        # Show the mouse when released, autohiding after the timeout
        self.ShowMouse(True)

        # Calling set mouse cursor with no parameter resets it to the default
        self.set_mouse_cursor()

    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        if self.sprite:
            if modifiers & key.MOD_COMMAND:
                # Draw the rectangle
                self.rectangle = pyglet.shapes.Rectangle(
                    self.xStartDrag, 
                    self.yStartDrag, 
                    x - self.xStartDrag, 
                    y - self.yStartDrag, 
                    (30, 144, 255), 
                    batch=self.batch,
                    group=self.foreground
                )

                # Set the opacity to 50%
                self.rectangle.opacity = 128
            else:
                # Update the x and y positions by the drag amounts
                self.sprite.x = self.sprite.x + dx
                self.sprite.y = self.sprite.y + dy

                # Clear the rectangle
                if self.rectangle:
                    self.rectangle.delete()
                    self.rectangle = None

def main() -> None:
    imageViewer = ImageViewer(sys.argv)

if __name__ == '__main__':
    main()
