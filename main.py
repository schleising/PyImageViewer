from pathlib import Path
import sys

from ImageViewer.FileTypes import supportedExtensions

from AppLauncher import AppLauncher

def PathValid(inputPath: Path) -> bool:
    # Check that the input path is a file and the suffix is supported
    return inputPath.is_file() and inputPath.suffix.lower() in supportedExtensions.values()

def main() -> None:
    if len(sys.argv) > 1 and PathValid(Path(sys.argv[1])):
        # If there is already a valid image on the command line, open it
        imagePath = Path(sys.argv[1])
    else:
        # With no image on the command line we need to check whether an image has
        # been double clicked in finder or the app opened on its own
        appLauncher = AppLauncher()

        # Get the filename from the app launcher
        imagePath = appLauncher.FilePath

    # If the file dialog has closed without a valid file being selected, exit
    if imagePath is None or not PathValid(imagePath):
        sys.exit()

    # Only import ImageViewer once the TkInter file dialog has closed
    from ImageViewer.ImageViewer import ImageViewer

    # Start the image viewer
    ImageViewer(imagePath)

if __name__ == '__main__':
    main()
