import logging
import multiprocessing as mp
from multiprocessing.connection import Connection
from multiprocessing.synchronize import Lock as LockBase
from pathlib import Path

from PIL import Image

from pyglet.image import ImageData

def poolInitialiser(inputLock: LockBase, conn: Connection, inLogQueue: mp.Queue) -> None:
    # Global variables to ensure they are shared between processes
    global lock
    global parentConn
    global logQueue

    # Lock for pipe access
    lock = inputLock

    # The parent pipe connection
    parentConn = conn

    # The log queue
    logQueue = inLogQueue

    # Log that the pools are initialising
    log('Initialising Pools', logging.DEBUG)

def log(message: str, level: int) -> None:
    # Send the message and level to the log queue
    logQueue.put_nowait((message, level))

def LoadImage(imagePath: Path, containerSize):
    # Try to load the image
    try:
        fullImage = Image.open(imagePath)
    except:
        # If the image cannot be loaded, log the error
        log(f'Loading {imagePath.name} Failed', logging.WARN)

        # Set image to None, this needs to be handled by the receiving end
        image = None
    else:
        try:
            # Create a thumnail of the image
            fullImage.thumbnail((containerSize, containerSize))
        except:
            # If the image cannot be loaded, log the error
            log(f'Failed to Create Thumbnail for {imagePath.name}', logging.WARN)

            # Set image to None, this needs to be handled by the receiving end
            image = None
        else:
            # Log that the image loaded as the thumbnail was created
            log(f'{imagePath.name} Loaded and Thumbnail Created', logging.DEBUG)

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
    parentConn.send((imagePath, image))
    lock.release()

class ThumbnailServer(mp.Process):
    def __init__(self, logQueue: mp.Queue) -> None:
        super(ThumbnailServer, self).__init__()

        # Set the log queue
        self.logQueue = logQueue

        # Create a lock to ensure this end of the pipe is accessed by one thread at a time
        self.lock = mp.Lock()

        # Create a Pipe to communicate with the file browser
        self.parentConn, self.childConn = mp.Pipe()

    def run(self) -> None:
        # Start a process pool to load and thumbnail the images
        with mp.Pool(initializer=poolInitialiser, initargs=(self.lock, self.parentConn, self.logQueue)) as pool:
            # Initialise the global data (queues, locks, pipes)
            poolInitialiser(self.lock, self.parentConn, self.logQueue)

            # Log that the server has started
            log('Starting Thumbnail Server', logging.DEBUG)

            # Run until told to stop
            while True:
                # Receive the imagePath, the path for container indexing and the size of the container
                imagePath, containerSize = self.parentConn.recv()

                if imagePath is not None and containerSize is not None:
                    # Add a job to the process pool to load and thumbnail the image
                    pool.apply_async(LoadImage, (imagePath, containerSize))
                else:
                    # If the application is closing, exit  the loop
                    break

            # Close the ends of the pipe using a lock to ensure a thread isn't accessing it (they should all have stopped by now anyway)
            self.parentConn.close()
            self.childConn.close()
