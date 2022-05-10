import multiprocessing as mp
from re import A
from threading import Thread, Lock
from pathlib import Path
from typing import Optional

from PIL import Image

from pyglet.image import ImageData

class ThumbnailServer:
    def __init__(self) -> None:
        self.process = mp.Process(target=self.mainLoop)
        self.parentConn, self.childConn = mp.Pipe()
        self.process.start()


    def mainLoop(self) -> None:
        lock = Lock()
        while True:
            imagePath, path, containerSize = self.parentConn.recv()

            if imagePath is not None and containerSize is not None:
                loadThread = Thread(target=self.LoadImage, args=(imagePath, path, containerSize, lock))
                loadThread.start()
            else:
                break

    def LoadImage(self, imagePath: Path, path: Path, containerSize, lock):
        fullImage = Image.open(imagePath)
        fullImage.thumbnail((containerSize, containerSize))

        mode = fullImage.mode
        formatLength = len(mode) if mode else 4
        rawImage = fullImage.tobytes()
        image = ImageData(fullImage.width, fullImage.height, mode, rawImage, -fullImage.width * formatLength)

        # rawImage = fullImage.tobytes()
        lock.acquire()
        self.parentConn.send((path, image))
        lock.release()
