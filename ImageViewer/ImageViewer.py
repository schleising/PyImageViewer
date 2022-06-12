from bisect import bisect
import logging
from datetime import datetime
from enum import Enum, auto
import math
from pathlib import Path
import time
from typing import Optional
import queue

import pyglet
from pyglet.window import key, mouse, Window
from pyglet.sprite import Sprite
from pyglet.image import ImageData, ImageDataRegion

from ImageViewer.FileBrowser import FileBrowser
from ImageViewer.ImageTools import Blur, Contour, Detail, EdgeEnhance, Emboss, FindEdges, Sharpen, Smooth
from ImageViewer.FileTypes import supportedExtensions

class Direction(Enum):
    Forward = auto()
    Back = auto()

class ImageViewer():
    def __init__(self, mainWindow: Window, logQueue: queue.Queue) -> None:

        # Set the main window
        self.mainWindow = mainWindow

        # Set the log queue
        self.logQueue = logQueue

        # The current image
        self.image: Optional[ImageData] = None

        # The original image to go back to if it has been manipulated
        self.originalImage: Optional[ImageData] = None
        self.originalXPos: int = 0
        self.originalYPos: int = 0
        self.originalScale: float = 0.0

        # Sprite containing the image
        self.sprite: Optional[Sprite] = None

        # Sprite containing the old image when scrolling in the new one
        self.oldSprite: Optional[Sprite] = None

        # Set safe defaults
        self.xStartDrag = 0
        self.yStartDrag = 0
        self.rectangle: Optional[pyglet.shapes.Rectangle] = None
        self.imageCanBeSaved: bool = False
        self.leftCommandHeld = False
        self.mouseX = 0
        self.mouseY = 0
        self.fps = 60
        self.startXPos = 0
        self.targetXPos = 0
        self.transitionTime = 0.5
        self.direction: Optional[Direction] = None
        self.startTransitionTime: Optional[float] = None
        self.bezierCurve: Optional[list[pyglet.shapes.Line]] = None
        # Set the P0 - P3 control points
        self.p0: tuple[float, float] = (0.0, 0.0)
        self.p1: tuple[float, float] = (0.25, 0.1)
        self.p2: tuple[float, float] = (0.25, 1.0)
        self.p3: tuple[float, float] = (1.0, 1.0)
        self.p0p1Line: Optional[pyglet.shapes.Line] = None
        self.p2p3Line: Optional[pyglet.shapes.Line] = None
        self.p1Circle: Optional[pyglet.shapes.Circle] = None
        self.p2Circle: Optional[pyglet.shapes.Circle] = None
        self.draggingP1Circle = False
        self.draggingP2Circle = False
        self.fileBrowser: Optional[FileBrowser] = None
        # Setup ordered groups to ensure shapes are drawn on top of the image
        self.background = pyglet.graphics.OrderedGroup(0)
        self.foreground = pyglet.graphics.OrderedGroup(1)

        # Create a batch drawing context
        self.batch = pyglet.graphics.Batch()

        # Create the initial Bezier curve
        self._CreateBezierCurve()

    def SetupImagePathAndLoadImage(self, inputPath: Path) -> None:
        # Check for a file on the command line
        if inputPath.is_file():
            # Get the parent folder
            imagePath = inputPath.parent

            # Get the list of image files in this folder
            self.images = self._GetImagePathList(imagePath)

            # Work out where in the list the current image is
            self.currentImageIndex = self.images.index(inputPath)
        else:
            # Get the images
            self.images = self._GetImagePathList(inputPath)

            # Set the index to 0
            self.currentImageIndex = 0

        # Set the maximum image index
        self.maxImageIndex = len(self.images) - 1

        # Load the image
        self._LoadImage()

        # Indicate the the image has now been initialised
        if self.fileBrowser:
            self.fileBrowser.imageViewerInitialised = True

    # Function to return a list of Paths pointing at images in the current folder
    def _GetImagePathList(self, imagePath: Path) -> list[Path]:
        # Return the list of images Paths, sorted alphabetically (case insensitive)
        return sorted([image for image in imagePath.iterdir() if image.suffix.lower() in supportedExtensions.values()], key=lambda x: x.name.lower())

    def _HideMouse(self, dt: float = 0.0) -> None:
        # Hide the mouse after the timeout expires
        self.mainWindow.set_mouse_visible(False)

    def _ShowMouse(self, autoHide: bool) -> None:
        # Unschedule the mouse hide callback
        pyglet.clock.unschedule(self._HideMouse)

        # Set the mouse to be visible
        self.mainWindow.set_mouse_visible(True)

        # If we want to hide the mouse again after a timeout, schedule the callback
        if autoHide:
            pyglet.clock.schedule_once(self._HideMouse, 0.5)

    def _LoadImage(self, imageRegion: Optional[ImageDataRegion] = None) -> None:
        if self.sprite:
            if self.direction is None:
                # Remove the existing sprite if it exists
                self.sprite.delete()
                self.sprite = None
            else:
                # Store the old sprite away
                self.oldSprite = self.sprite

        # Remove the existing rectangle if it exists
        if self.rectangle:
            self.rectangle.delete()
            self.rectangle = None

        if imageRegion:
            self.image = imageRegion
            self.imageCanBeSaved = True
            loadingImage = False
        else:
            # Load the new image
            self.image = pyglet.image.load(self.images[self.currentImageIndex])
            self.originalImage = self.image
            self.imageCanBeSaved = False
            loadingImage = True

        # Scale and position the image to fit the window
        self._ScaleImage(loadingImage)

    def _ScaleImage(self, loadingImage: bool) -> None:
        if self.image:
            # Work out how much to scale each axis to fit into the screen
            xScale = self.mainWindow.width / self.image.width
            yScale = self.mainWindow.height / self.image.height

            # Both axes need to be scaled by the smallest number
            scalingFactor = min(xScale, yScale)

            # Calculate the x and y position needed to draw the image in the centre of the screen
            xPos = self.mainWindow.width / 2 - (scalingFactor * self.image.width / 2)
            yPos = self.mainWindow.height / 2 - (scalingFactor * self.image.height / 2)

            # Work out where in x we want the new image to stop scrolling in
            self.targetXPos = xPos

            if self.direction == Direction.Forward:
                # Work out the off screen x position for the new image to start
                xPos = xPos + self.mainWindow.width
            elif self.direction == Direction.Back:
                # Work out the off screen x position for the new image to start
                xPos = xPos - self.mainWindow.width

            # Store the starting position for use in calculating the transition
            self.startXPos = xPos

            # Create a sprite containing the image at the calculated x, y position
            self.sprite = pyglet.sprite.Sprite(img=self.image, x=xPos, y=yPos, batch=self.batch, group=self.background)

            # Scale the sprite
            self.sprite.scale = scalingFactor

            if loadingImage:
                # Save the original position
                self.originalXPos = xPos
                self.originalYPos = yPos

                # Save the original scale
                self.originalScale = scalingFactor

            print(scalingFactor)

            # Hide the mouse immediately
            self._HideMouse()

            if self.direction is not None:
                # Schedule an animation frame at the desired frame rate
                pyglet.clock.schedule_interval(self._AnimateNewImage, 1 / self.fps)

    def _CalculateBezierPoint(self, t: float) -> tuple[float, float]:
        # Initialise the returned point to 0, 0
        point: list[float] = [0, 0]

        # Calculate x and y
        for i in range(2):
            point[i] = ((1 - t)**3 * self.p0[i]) + (3 * (1 - t)**2 * t * self.p1[i]) + (3 * (1 - t) * t**2 * self.p2[i]) + (t**3 * self.p3[i])

        # Return the calculated point
        return tuple(point)

    def _CreateBezierCurve(self):
        # Create a list of points on a Bezier curve, first ensure the number of points on the curve is adequate
        framesInTransition = math.ceil(self.fps * self.transitionTime)

        # Calculate the points given the ideal frame numbers, storing them in point list as a lookup table
        self.pointList = [self._CalculateBezierPoint(t / framesInTransition) for t in range(framesInTransition + 1)]

        # Get the x and y points into individual lists to use later with bisect
        self.xPoints = [x for x, y in self.pointList]
        self.yPoints = [y for x, y in self.pointList]

    def _GetBezierMovementRatio(self, t: float) -> float:
        # Get the index of t within the x points
        index = bisect(self.xPoints, t)

        if index <= 0:
            # Return the first point if the index is 0 or less
            return self.yPoints[0]
        elif index >= len(self.yPoints):
            # Return the last point of the index is the length of the list or greater
            return self.yPoints[-1]

        # Work out how far between the nearest two points t is
        xFraction = (t - self.xPoints[index-1]) / (self.xPoints[index] - self.xPoints[index - 1])

        # Use this to interpolate between the two y points related to this value of t
        y = self.yPoints[index-1] + ((self.yPoints[index] - self.yPoints[index-1]) * xFraction)

        # Return the interpolated y point associated with this t
        return y

    def _AnimateNewImage(self, dt) -> None:
        if self.sprite and self.oldSprite:
            # Set the start transition time if it has not yet been started
            if self.startTransitionTime is None:
                self.startTransitionTime = time.time()

            # Get the time now
            timeNow = time.time()

            # Calculate the amount of time through the transition we are (complete = 1)
            timeFactor = (timeNow - self.startTransitionTime) / self.transitionTime

            # Use the Bezier lookup table to get the movement factor (y) from the time factor (x)
            transitionFactor = self._GetBezierMovementRatio(timeFactor)

            # Use this factor to calculate the new x position
            newXPos = self.startXPos + ((self.targetXPos - self.startXPos) * transitionFactor)

            # Move the two sprites to the new x positions
            self.oldSprite.x += newXPos - self.sprite.x
            self.sprite.x = newXPos

            # Check whether the scrolling time has elapsed
            if timeFactor > 1:
                # Set the sprite x to the target position in case there are rounding errors
                self.sprite.x = self.targetXPos

                # Unschedule the animation
                pyglet.clock.unschedule(self._AnimateNewImage)

                # Delete the old sprite
                self.oldSprite.delete()
                self.oldSprite = None

                # Reset the scroll direction to None
                self.direction = None

                # Reset the start transition time to None
                self.startTransitionTime = None

    def _ConstrainToSprite(self, x: int, y: int) -> tuple[int, int]:
        # Initialise x and y to 0
        xPos = 0
        yPos = 0

        if self.sprite:
            # Constrain x to the sprite dimensions
            if x < self.sprite.x:
                xPos = self.sprite.x
            elif x >= self.sprite.x + self.sprite.width:
                xPos = self.sprite.x + self.sprite.width
            else:
                xPos = x

            # Constrain y to the sprite dimensions
            if y < self.sprite.y:
                yPos = self.sprite.y
            elif y >= self.sprite.y + self.sprite.height:
                yPos = self.sprite.y + self.sprite.height
            else:
                yPos = y

        # Return the constrained x and y positions
        return xPos, yPos

    def _CropImage(self, cropToScreen: bool) -> None:
        # If the sprite and image are valid
        if self.sprite and self.image:
            if cropToScreen:
                # Get the screen x and y coordinates of the bottom left
                screenX, screenY = 0, 0

                # Get the screen width and height
                screenWidth = self.mainWindow.width
                screenHeight = self.mainWindow.height
            elif self.rectangle:
                # Get the screen x and y coordinates of the rectangle
                screenX, screenY = self.rectangle.position

                # Get the screen width and height of the rectangle
                screenWidth = self.rectangle.width
                screenHeight = self.rectangle.height
            else:
                # Get the screen x and y coordinates of the bottom left
                screenX, screenY = 0, 0

                # Get the screen width and height
                screenWidth = self.mainWindow.width
                screenHeight = self.mainWindow.height

            # Ensure that the x and y of the rectangle are bottom left
            if screenWidth < 0:
                screenX = screenX + screenWidth

            if screenHeight < 0:
                screenY = screenY + screenHeight

            # Ensure that the width and height of the rectangle are positive
            screenWidth = abs(screenWidth)
            screenHeight = abs(screenHeight)

            # Get the screen x and y of the sprite origin
            spriteOriginX, spriteOriginY = self.sprite.position

            # Find out how far into the image we are in left and right in screen pixels
            scaledImageX = screenX - spriteOriginX
            scaledImageY = screenY - spriteOriginY

            # Get the sprite scaling factor
            scalingFactor = self.sprite.scale

            # Get the x, y, width and height in image pixels, ensuring the region is within the image bounds
            imageX = int(max(scaledImageX / scalingFactor, 0))
            imageY = int(max(scaledImageY / scalingFactor, 0))
            imageWidth = int(min(screenWidth / scalingFactor, self.image.width))
            imageHeight = int(min(screenHeight / scalingFactor, self.image.height))

            # Get this region of the image
            imageRegion = self.image.get_region(imageX, imageY, imageWidth, imageHeight)

            # Display the cropped image
            self._LoadImage(imageRegion)

    def _SaveImage(self) -> None:
        # If the image can be saved (i.e., it is modified)
        if self.image and self.imageCanBeSaved:
            # Get the filename of the original image
            originalFilename = self.images[self.currentImageIndex]

            # Construct a new filename using .png as the suffix
            newFilename = originalFilename.parent / f'{originalFilename.stem}_Cropped {datetime.now()}.png'

            # Save the new file
            self.image.save(newFilename)

            # Add the new image to the list
            self.images.insert(self.currentImageIndex + 1, newFilename)

            # Make this image the current one
            self.currentImageIndex = self.images.index(newFilename)

    def _ShowBezierCurve(self) -> None:
        # Zip the points with the next point to produce a list of lines
        lineList = zip(self.pointList, self.pointList[1:])

        # Create the Bezier curve
        self.bezierCurve = [pyglet.shapes.Line(
            x1 * (self.mainWindow.width / 2) + (self.mainWindow.width / 4),
            y1 * (self.mainWindow.height / 2) + (self.mainWindow.height / 4),
            x2 * (self.mainWindow.width / 2) + (self.mainWindow.width / 4),
            y2 * (self.mainWindow.height / 2) + (self.mainWindow.height / 4),
            batch=self.batch,
            group=self.foreground,
            color=(255, 0, 0),
            width=3
        ) for (x1, y1), (x2, y2) in lineList]

        # Create a line showing the P0 -> P1 control line
        self.p0p1Line = pyglet.shapes.Line(
            self.p0[0] * (self.mainWindow.width / 2) + (self.mainWindow.width / 4),
            self.p0[1] * (self.mainWindow.height / 2) + (self.mainWindow.height / 4),
            self.p1[0] * (self.mainWindow.width / 2) + (self.mainWindow.width / 4),
            self.p1[1] * (self.mainWindow.height / 2) + (self.mainWindow.height / 4),
            batch=self.batch,
            group=self.foreground,
            color=(0, 255, 0),
            width=5
        )

        # Create a circle for P1
        self.p1Circle = pyglet.shapes.Circle(
            self.p1[0] * (self.mainWindow.width / 2) + (self.mainWindow.width / 4),
            self.p1[1] * (self.mainWindow.height / 2) + (self.mainWindow.height / 4),
            radius=10,
            color=(0, 255, 0),
            batch=self.batch,
            group=self.foreground
        )

        # Create a line showing the P2 -> P3 control line
        self.p2p3Line = pyglet.shapes.Line(
            self.p2[0] * (self.mainWindow.width / 2) + (self.mainWindow.width / 4),
            self.p2[1] * (self.mainWindow.height / 2) + (self.mainWindow.height / 4),
            self.p3[0] * (self.mainWindow.width / 2) + (self.mainWindow.width / 4),
            self.p3[1] * (self.mainWindow.height / 2) + (self.mainWindow.height / 4),
            batch=self.batch,
            group=self.foreground,
            color=(0, 0, 255),
            width=5
        )

        # Create a circle for P2
        self.p2Circle = pyglet.shapes.Circle(
            self.p2[0] * (self.mainWindow.width / 2) + (self.mainWindow.width / 4),
            self.p2[1] * (self.mainWindow.height / 2) + (self.mainWindow.height / 4),
            radius=10,
            color=(0, 0, 255),
            batch=self.batch,
            group=self.foreground
        )

    def _HideBezierCurve(self) -> None:
        if self.bezierCurve:
            # If the Bezier curve is shown, delete the lines making itb up
            for line in self.bezierCurve:
                line.delete()

            # Set the list to None
            self.bezierCurve = None

        if self.p0p1Line:
            # Delete the line
            self.p0p1Line.delete()

            # set the line to None
            self.p0p1Line = None

        if self.p1Circle:
            # Delete the circle
            self.p1Circle.delete()

            # set the circle to None
            self.p1Circle = None

        if self.p2p3Line:
            # Delete the line
            self.p2p3Line.delete()

            # set the line to None
            self.p2p3Line = None

        if self.p2Circle:
            # Delete the circle
            self.p2Circle.delete()

            # set the circle to None
            self.p2Circle = None

    def on_draw(self):
        # Draw the batch
        self.batch.draw()

    def on_key_press(self, symbol, modifiers):
        if modifiers & key.MOD_COMMAND:
            # If the Command button is pressed this is an image manipulation command
            if symbol == key.S:
                self._Sharpen()
                return
            elif symbol == key.B:
                self._Blur()
                return
            elif symbol == key.C:
                self._Contour()
                return
            elif symbol == key.D:
                self._Detail()
                return
            elif symbol == key.E:
                self._EdgeEnhance()
                return
            elif symbol == key.M:
                self._Emboss()
                return
            elif symbol == key.F:
                self._FindEdges()
                return
            elif symbol == key.O:
                self._Smooth()
                return
            elif symbol == key.Z:
                self._RestoreOriginalImage()
                return
            else:
                return
        elif symbol == key.B:
            if self.bezierCurve:
                # If the Bezier curve is shown, delete it
                self._HideBezierCurve()
                return
            else:
                # If the Bezier curve is not shown, create and show it
                self._ShowBezierCurve()
                return
        elif symbol == key.UP:
            # Open the file browser window with the current image parent path
            self.mainWindow.toggleViewer()

            # Ensure the mouse isn't hidden
            self._ShowMouse(False)

            # Exit this handler
            return
        # Ignore the request if the previous scroll is still ongoing
        elif self.direction is None:
            if symbol == key.RIGHT:
                # Crop the image before setting the scroll direction
                self._CropImage(cropToScreen=True)

                # Set the scroll direction
                self.direction = Direction.Forward

                # Increment the image index
                self.currentImageIndex += 1

                # Check that the new index is in bounds
                if self.currentImageIndex > self.maxImageIndex:
                    # Reset to 0 if not
                    self.currentImageIndex = 0
            elif symbol == key.LEFT:
                # Crop the image before setting the scroll direction
                self._CropImage(cropToScreen=True)

                # Set the scroll direction
                self.direction = Direction.Back

                # Decrement the image index
                self.currentImageIndex -= 1

                # Check that the new index is in bounds
                if self.currentImageIndex < 0:
                    # Set to the max index value if not
                    self.currentImageIndex = self.maxImageIndex
            elif symbol == key.C:
                # Ensure the scroll direction is set to None
                self.direction = None

                # Crop the image
                self._CropImage(cropToScreen=False)

                # Return without reloading the image
                return
            elif symbol == key.S:
                # If the rectangle has been drawn
                if self.imageCanBeSaved:
                    # Crop the image
                    self._SaveImage()

                # Return without reloading the image
                return
            elif symbol == key.LCTRL:
                # Clear the rectangle
                if self.rectangle:
                    self.rectangle.delete()
                    self.rectangle = None

                # Log that the left command key is held down
                self.leftCommandHeld = True

                # Log the starting point of the rectangle
                self.xStartDrag, self.yStartDrag = self._ConstrainToSprite(self.mouseX, self.mouseY)

                # Get the crosshair cursor
                cursor = self.mainWindow.get_system_mouse_cursor(self.mainWindow.CURSOR_CROSSHAIR)

                # Set the crosshair as the current cursor
                self.mainWindow.set_mouse_cursor(cursor)

                # Show the mouse without autohiding
                self._ShowMouse(False)

                # Return without reloading the image
                return
            else:
                # If this is not one of the above keys return without redrawing the image
                return
        else:
            # If a scroll is still ongoing return without taking any action
            return

        # Clear the rectangle
        if self.rectangle:
            self.rectangle.delete()
            self.rectangle = None

        # Load the new image
        self._LoadImage()

    def on_key_release(self, symbol, modifiers):
        if symbol == key.LCTRL:
            # Clear the left command key held status
            self.leftCommandHeld = False

            # Calling set mouse cursor with no parameter resets it to the default
            self.mainWindow.set_mouse_cursor()

            # Show the mouse when it moves, autohiding afterwards
            self._ShowMouse(True)

    def on_mouse_motion(self, x, y, dx, dy):
        # Store the current mouse x and y position
        self.mouseX = x
        self.mouseY = y

        if self.leftCommandHeld:
            # Get the x and y position constrained to the image
            xPos, yPos = self._ConstrainToSprite(x, y)

            # Draw the rectangle
            self.rectangle = pyglet.shapes.Rectangle(
                self.xStartDrag,
                self.yStartDrag,
                xPos - self.xStartDrag,
                yPos - self.yStartDrag,
                (30, 144, 255),
                batch=self.batch,
                group=self.foreground
            )

            # Set the opacity to 50%
            self.rectangle.opacity = 128

            # Show the mouse when it moves, not autohiding
            self._ShowMouse(False)
        else:
            # Show the mouse when it moves, autohiding afterwards
            self._ShowMouse(True)

    def on_mouse_scroll(self, x, y, scroll_x, scroll_y):
        # Show the mouse when scrolling, autohiding afterwards
        self._ShowMouse(True)

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
        if button == mouse.LEFT:
            # Show the mouse while pressed, do not autohide
            self._ShowMouse(False)

            # Clear the left command key held status
            self.leftCommandHeld = False

            # Clear the rectangle
            if self.rectangle:
                self.rectangle.delete()
                self.rectangle = None

            # Get the hand cursor
            cursor = self.mainWindow.get_system_mouse_cursor(self.mainWindow.CURSOR_HAND)

            # Set the hand as the current cursor
            self.mainWindow.set_mouse_cursor(cursor)
        elif button == mouse.RIGHT:
            # Quit the application
            self.logQueue.put_nowait(('Exiting Pyglet application', logging.DEBUG))
            pyglet.app.exit()

    def on_mouse_release(self, x, y, button, modifiers):
        # Show the mouse when released, autohiding after the timeout
        self._ShowMouse(True)

        # Calling set mouse cursor with no parameter resets it to the default
        self.mainWindow.set_mouse_cursor()

        # Clear the circle dragging flags
        self.draggingP1Circle = False
        self.draggingP2Circle = False

    def _MouseInCircle(self, x, y, circle: pyglet.shapes.Circle) -> bool:
        # Get the x and y distance from the circle
        xDelta = abs(x - circle.x)
        yDelta = abs(y - circle.y)

        # Use this to get the absolute distance from the circle
        distanceFromCentre = math.sqrt(xDelta**2 + yDelta**2)

        # Return True if this distance is less than the circle radius, otherwise False
        return distanceFromCentre <= circle.radius

    def _ConstrainToScreen(self, x, y) -> tuple[float, float]:
        # Constrain the point to the screen in x
        if x < 0:
            x = 0
        elif x > self.mainWindow.width - 1:
            x = self.mainWindow.width -1

        # Constrain the point to the screen in y
        if y < 0:
            y = 0
        elif y > self.mainWindow.height - 1:
            y = self.mainWindow.height -1

        # Return x and y as a tuple
        return x, y

    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        if self.p1Circle and not self.draggingP2Circle and (self.draggingP1Circle or self._MouseInCircle(x, y, self.p1Circle)):
            # Set the draggin P1 flag to True
            self.draggingP1Circle = True

            # Update the x and y position of the circle
            self.p1Circle.x += dx
            self.p1Circle.y += dy

            # Constrain the circle to the screen
            self.p1Circle.position = self._ConstrainToScreen(self.p1Circle.x, self.p1Circle.y)

            # Work out the new P1 control point position
            self.p1 = (2 * (((self.p1Circle.x - self.mainWindow.width / 4) / self.mainWindow.width)), 
                2 * (((self.p1Circle.y - self.mainWindow.height / 4) / self.mainWindow.height)))

            # Update the Bezier curve
            self._CreateBezierCurve()

            # Show the new Bezier curve and control lines / points
            self._ShowBezierCurve()
        elif self.p2Circle and not self.draggingP1Circle and (self.draggingP2Circle or self._MouseInCircle(x, y, self.p2Circle)):
            # Set the draggin P1 flag to True
            self.draggingP2Circle = True

            # Update the x and y position of the circle
            self.p2Circle.x += dx
            self.p2Circle.y += dy

            # Constrain the circle to the screen
            self.p2Circle.position = self._ConstrainToScreen(self.p2Circle.x, self.p2Circle.y)

            # Work out the new P1 control point position
            self.p2 = (2 * (((self.p2Circle.x - self.mainWindow.width / 4) / self.mainWindow.width)),
                2 * (((self.p2Circle.y - self.mainWindow.height / 4) / self.mainWindow.height)))

            # Update the Bezier curve
            self._CreateBezierCurve()

            # Show the new Bezier curve and control lines / points
            self._ShowBezierCurve()
        elif self.sprite:
            # Update the x and y positions by the drag amounts
            self.sprite.x = self.sprite.x + dx
            self.sprite.y = self.sprite.y + dy

            # Clear the rectangle
            if self.rectangle:
                self.rectangle.delete()
                self.rectangle = None

    def _Sharpen(self) -> None:
        if self.image and self.sprite:
            # Create a Pyglet ImageData object from the bytes
            self.image = Sharpen(self.image)

            # Set the sprite image to the new image
            self.sprite.image = self.image

    def _Blur(self) -> None:
        if self.image and self.sprite:
            # Create a Pyglet ImageData object from the bytes
            self.image = Blur(self.image)

            # Set the sprite image to the new image
            self.sprite.image = self.image

    def _Contour(self) -> None:
        if self.image and self.sprite:
            # Create a Pyglet ImageData object from the bytes
            self.image = Contour(self.image)

            # Set the sprite image to the new image
            self.sprite.image = self.image

    def _Detail(self) -> None:
        if self.image and self.sprite:
            # Create a Pyglet ImageData object from the bytes
            self.image = Detail(self.image)

            # Set the sprite image to the new image
            self.sprite.image = self.image

    def _EdgeEnhance(self) -> None:
        if self.image and self.sprite:
            # Create a Pyglet ImageData object from the bytes
            self.image = EdgeEnhance(self.image)

            # Set the sprite image to the new image
            self.sprite.image = self.image

    def _Emboss(self) -> None:
        if self.image and self.sprite:
            # Create a Pyglet ImageData object from the bytes
            self.image = Emboss(self.image)

            # Set the sprite image to the new image
            self.sprite.image = self.image

    def _FindEdges(self) -> None:
        if self.image and self.sprite:
            # Create a Pyglet ImageData object from the bytes
            self.image = FindEdges(self.image)

            # Set the sprite image to the new image
            self.sprite.image = self.image

    def _Smooth(self) -> None:
        if self.image and self.sprite:
            # Create a Pyglet ImageData object from the bytes
            self.image = Smooth(self.image)

            # Set the sprite image to the new image
            self.sprite.image = self.image

    def _RestoreOriginalImage(self) -> None:
        if self.image and self.sprite:
            # Restore the original image
            self.image = self.originalImage

            # Restore the sprite image
            self.sprite.image = self.image

            # Restore the sprite position
            self.sprite.x = self.originalXPos
            self.sprite.y = self.originalYPos

            # Restore the original scaling
            self.sprite.scale = self.originalScale
