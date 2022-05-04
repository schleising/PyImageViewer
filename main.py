from pathlib import Path
import sys

from ImageViewer.FileTypes import supportedExtensions

def PathValid(inputPath: Path) -> bool:
    # Check that the input path is a file and the suffix is supported
    return inputPath.is_file and inputPath.suffix in supportedExtensions.values()

def main() -> None:
    if len(sys.argv) > 1 and PathValid(Path(sys.argv[1])):
        # If there is already a valid image on the command line, open it
        imagePath = Path(sys.argv[1])
    else:
        # Otherwise open a dialog to get the user to select a file
        import tkinter as tk
        from tkinter import filedialog

        # Create a TkInter app
        root = tk.Tk()

        # Hide the main window
        root.withdraw()

        # Open the folder chooser dialog
        imagePath = Path(filedialog.askopenfilename(filetypes=list(supportedExtensions.items()), initialdir=Path.home() / 'Pictures'))

        # If the file dialog has closed without a valid file being selected, exit
        if not PathValid(imagePath):
            sys.exit()

    # Only import ImageViewer once the TkInter file dialog has closed
    from ImageViewer.ImageViewer import ImageViewer

    # Start the image viewer
    ImageViewer(imagePath)

if __name__ == '__main__':
    main()
