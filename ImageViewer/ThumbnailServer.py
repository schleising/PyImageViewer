import multiprocessing as mp
from threading import Thread, Lock
from pathlib import Path

from PIL import Image

from pyglet.image import ImageData

class ThumbnailServer:
    def __init__(self) -> None:
        # Flagto indicate that the Process is being closed
        self.closing = False

        # The process itself
        self.process = mp.Process(target=self.mainLoop)

        # Create a Pip to communicate with the file browser
        self.parentConn, self.childConn = mp.Pipe()

        # Start the process
        self.process.start()

    def mainLoop(self) -> None:
        # Create a lock to ensure this end of the pipe is accessed by one thread at a time
        lock = Lock()

        # Run until told to stop
        while True:
            # Receive the imagePath, the path for container indexing and the size of the container
            imagePath, path, containerSize = self.parentConn.recv()

            if imagePath is not None and containerSize is not None:
                # Create and start a thread to load and thumbnail the image
                loadThread = Thread(target=self.LoadImage, args=(imagePath, path, containerSize, lock))
                loadThread.start()
            else:
                # If the application is closing, exit  the loop
                break

        # Indicate that the process is closing
        self.closing = True

        # If there ane messages in the pipe, recive them to clear the pipe down and allow threads to exit
        while self.childConn.poll():
            self.childConn.recv()

        # Close the ends of the pipe using a lock to ensure a thread isn't accessing it (they should all have stopped by now anyway)
        lock.acquire()
        self.parentConn.close()
        self.childConn.close()
        lock.release()

    def LoadImage(self, imagePath: Path, path: Path, containerSize, lock):
        # Load the image
        fullImage = Image.open(imagePath)

        # Create a thumnail of the image
        fullImage.thumbnail((containerSize, containerSize))

        # Get the mode (e.g., 'RGBA')
        mode = fullImage.mode

        # Get the number of bytes per pixel
        formatLength = len(mode) if mode else 4

        # Convert the image to bytes
        rawImage = fullImage.tobytes()

        # Create a Pyglet ImageData object from the bytes
        image = ImageData(fullImage.width, fullImage.height, mode, rawImage, -fullImage.width * formatLength)

        # Get a lock and, if the Process isn't shutting down, send the path and image back to the file browser
        lock.acquire()
        if not self.closing:
            self.parentConn.send((path, image))
        lock.release()
