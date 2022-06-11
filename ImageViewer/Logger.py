import logging
from pathlib import Path
import threading
import queue

class Logger:
    def __init__(self, level: int = logging.INFO) -> None:
        # Set the log level
        self.level = level

        # Create the logging thread
        self.process = threading.Thread(target=self.LoggingThread)

        # Create a message queue
        self.messageQueue = queue.Queue()

        # Start the logging process
        self.process.start()

    def LoggingThread(self) -> None:
        # Setup the logfile
        logging.basicConfig(
            filename=Path.home() / '.PyImageViewerLog.txt',
            level=self.level,
            format='%(asctime)s:%(levelname)s:%(message)s'
        )

        # Loop until the application is Exiting
        while True:
            # Get the message and level from the queue
            message, level = self.messageQueue.get()

            # Log the message            
            logging.log(level=level, msg=message)

            if message == 'Exiting':
                # If the application is closing, break out of the loop
                break
