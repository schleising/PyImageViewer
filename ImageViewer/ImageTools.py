from PIL import Image, ImageFilter

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

def Sharpen(inputImage: ImageData) -> ImageData:
    # Convert the pyglet ImageData to a Pillow Image
    pilImage = PygletToPillow(inputImage)

    # Sharpen the image
    sharpenedPilImage = pilImage.filter(ImageFilter.SHARPEN)

    # Return the image as a Pyglet ImageData type
    return PillowToPyglet(sharpenedPilImage)
