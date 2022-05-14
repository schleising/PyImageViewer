import logging
from pathlib import Path
import multiprocessing as mp

class Logger:
    def __init__(self, level: int = logging.INFO) -> None:
        # Set the log level
        self.level = level

        # Create the logging process
        self.process = mp.Process(target=self.LoggingProcess)

        # Create a message queue
        self.messageQueue = mp.Queue()

        # Start the logging process
        self.process.start()

    def LoggingProcess(self) -> None:
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

        # Close the message queue
        self.messageQueue.close()
