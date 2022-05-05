import logging
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog
from typing import Optional

from ImageViewer.FileTypes import supportedExtensions

class AppLauncher:
    def __init__(self) -> None:
        # Set the initial folder
        self.InitialDir: Path = Path.home() / 'Pictures'

        # Check this folder actually exists, if not, revert to the home folder
        if not self.InitialDir.is_dir():
            self.InitialDir = Path.home()

        # Set FilePath to None for now
        self.FilePath: Optional[Path] = None

        # Create the Tk app
        self.root = tk.Tk()

        # Hide the main Tk window
        self.root.withdraw()

        # Create a callback for the OpenDocument message from the MacOS
        self.root.createcommand("::tk::mac::OpenDocument", self._GetFilePath)

        # Create a delayed callback to check whether a file was sent to the application
        self.root.after(400, self._DelayedFunction)

        # Start the mainloop to service the callbacks
        logging.info('Starting Tk mainloop')
        self.root.mainloop()

    def _GetFilePath(self, *args) -> None:
        # Log that we are in this function
        logging.info('in _GetFilePath()')

        # Log the files sent to this application (should only be one)
        for arg in args:
            logging.info(arg)

        # Get the file into a path variable
        if args:
            self.FilePath = Path(args[0])

            # Stop the Tk mainloop if we have set the file name
            logging.info('Exiting Tk mainloop')
            self.root.quit()

    def _DelayedFunction(self) -> None:
        # Log that we are in this function
        logging.info('in _DelayedFunction()')

        # If the file has not yet been set via the finder window
        if self.FilePath is None:
            # Open the folder chooser dialog
            self.FilePath = Path(filedialog.askopenfilename(filetypes=list(supportedExtensions.items()), initialdir=self.InitialDir))

        # Stop the Tk mainloop
        logging.info('Exiting Tk mainloop')
        self.root.quit()
