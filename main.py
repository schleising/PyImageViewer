import logging
from pathlib import Path

from ImageViewer.ImageViewer import ImageViewer

def main() -> None:
    # Setup the logfile
    logging.basicConfig(
        filename=Path.home() / '.PyImageViewerLog.txt',
        level=logging.INFO,
        format='%(asctime)s:%(levelname)s:%(message)s'
    )

    # Log that the app has started
    logging.info('App Started')

    # Start the image viewer
    ImageViewer(fullScreenAllowed=True)

if __name__ == '__main__':
    main()
