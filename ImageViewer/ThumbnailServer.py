import logging
import threading
import queue
import concurrent.futures
from pathlib import Path

from PIL import Image

from ImageViewer.ImageTools import PillowToPyglet

class ThumbnailServer(threading.Thread):
    def __init__(self, logQueue: queue.Queue) -> None:
        super(ThumbnailServer, self).__init__()

        # Set the log queue
        self.logQueue = logQueue

        # Create a lock to ensure the queue is accessed by one thread at a time
        self.lock = threading.Lock()

        # Create a queue to send to the Thnumbnail Server
        self.toTS = queue.Queue()

        # Create a queue to send from the Thnumbnail Server
        self.fromTS = queue.Queue()

    def run(self) -> None:
        # Start a process pool to load and thumbnail the images
        with concurrent.futures.ThreadPoolExecutor() as pool:
            # Log that the server has started
            self.log('Starting Thumbnail Server', logging.DEBUG)

            # Run until told to stop
            while True:
                # Receive the imagePath, the path for container indexing and the size of the container
                imagePath, containerSize = self.toTS.get()

                if imagePath is not None and containerSize is not None:
                    # Add a job to the process pool to load and thumbnail the image
                    pool.submit(self.LoadImage, imagePath, containerSize)
                else:
                    # If the application is closing, exit  the loop
                    break

    def log(self, message: str, level: int) -> None:
        # Send the message and level to the log queue
        self.logQueue.put_nowait((message, level))

    def LoadImage(self, imagePath: Path, containerSize):
        # Try to load the image
        try:
            fullImage = Image.open(imagePath)
        except:
            # If the image cannot be loaded, log the error
            self.log(f'Loading {imagePath.name} Failed', logging.WARN)

            # Set image to None, this needs to be handled by the receiving end
            image = None
        else:
            try:
                # Create a thumnail of the image
                fullImage.thumbnail((containerSize, containerSize))
            except:
                # If the image cannot be loaded, log the error
                self.log(f'Failed to Create Thumbnail for {imagePath.name}', logging.WARN)

                # Set image to None, this needs to be handled by the receiving end
                image = None
            else:
                # Log that the image loaded as the thumbnail was created
                self.log(f'{imagePath.name} Loaded and Thumbnail Created', logging.DEBUG)

                # Create a Pyglet ImageData object from the bytes
                image = PillowToPyglet(fullImage)

        # Get a lock and, if the Process isn't shutting down, send the path and image back to the file browser
        with self.lock:
            self.fromTS.put_nowait((imagePath, image))
