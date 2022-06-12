from typing import Callable
from PIL import Image, ImageFilter
from PIL.ImageFilter import Filter

from pyglet.image import ImageData

def PygletToPillow(inputImage: ImageData) -> Image.Image:
    # Convert the pyglet ImageData to a Pillow Image
    return Image.frombytes('RGBA', (inputImage.width, inputImage.height), inputImage.get_data())

def PillowToPyglet(inputImage: Image.Image) -> ImageData:
    # Get the mode (e.g., 'RGBA')
    mode = inputImage.mode

    # Get the number of bytes per pixel
    formatLength = len(mode) if mode else 4

    # Convert the image to bytes
    rawImage = inputImage.tobytes()

    # Create a Pyglet ImageData object from the bytes and return it
    return ImageData(inputImage.width, inputImage.height, mode, rawImage, -inputImage.width * formatLength)

def _ManipulateImage(inputImage: ImageData, filter: Filter | Callable[[], Filter]) -> ImageData:
    # Convert the pyglet ImageData to a Pillow Image
    pilImage = PygletToPillow(inputImage)

    # Manipulate the image
    manipulatedPilImage = pilImage.filter(filter)

    # Return the image as a Pyglet ImageData type
    return PillowToPyglet(manipulatedPilImage)

def Sharpen(inputImage: ImageData) -> ImageData:
    # Sharpen the image
    return _ManipulateImage(inputImage, ImageFilter.SHARPEN)

def Blur(inputImage: ImageData) -> ImageData:
    # Blur the image
    return _ManipulateImage(inputImage, ImageFilter.BLUR)

def Contour(inputImage: ImageData) -> ImageData:
    # Contour the image
    return _ManipulateImage(inputImage, ImageFilter.CONTOUR)

def Detail(inputImage: ImageData) -> ImageData:
    # Detail the image
    return _ManipulateImage(inputImage, ImageFilter.DETAIL)

def EdgeEnhance(inputImage: ImageData) -> ImageData:
    # Edge enhance the image
    return _ManipulateImage(inputImage, ImageFilter.EDGE_ENHANCE)

def Emboss(inputImage: ImageData) -> ImageData:
    # Emboss the image
    return _ManipulateImage(inputImage, ImageFilter.EMBOSS)

def FindEdges(inputImage: ImageData) -> ImageData:
    # Find Edges the image
    return _ManipulateImage(inputImage, ImageFilter.FIND_EDGES)

def Smooth(inputImage: ImageData) -> ImageData:
    # Smooth the image
    return _ManipulateImage(inputImage, ImageFilter.SMOOTH)
