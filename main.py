import logging
from pathlib import Path
import sys

from ImageViewer.FileTypes import supportedExtensions

from AppLauncher import AppLauncher

def PathValid(inputPath: Path) -> bool:
    # Check that the input path is a file and the suffix is supported
    return inputPath.is_file() and inputPath.suffix.lower() in supportedExtensions.values()

def main() -> None:
    # Setup the logfile
    logging.basicConfig(
        filename=Path.home() / '.PyImageViewerLog.txt',
        level=logging.INFO,
        format='%(asctime)s:%(levelname)s:%(message)s'
    )

    # Log that the app has started
    logging.info('App Started')

    if len(sys.argv) > 1 and PathValid(Path(sys.argv[1])):
        # If there is already a valid image on the command line, open it
        imagePath = Path(sys.argv[1])

        # Log that we got the image from the command line
        logging.info('Got image from command line')
    else:
        # With no image on the command line we need to check whether an image has
        # been double clicked in finder or the app opened on its own
        appLauncher = AppLauncher()

        # Get the filename from the app launcher
        imagePath = appLauncher.FilePath

        # Log that we got the image from the App Launcher
        logging.info('Got image from App Launcher')

    # If the file dialog has closed without a valid file being selected, exit
    if imagePath is None or not PathValid(imagePath):
        # Log that there was an error
        logging.info(f'Exiting, image path: {imagePath} is invalid')

        # Exit
        sys.exit()

    # Only import ImageViewer once the TkInter file dialog has closed
    from ImageViewer.ImageViewer import ImageViewer

    # Start the image viewer
    logging.info('Starting viewer')
    ImageViewer(imagePath)

if __name__ == '__main__':
    main()
