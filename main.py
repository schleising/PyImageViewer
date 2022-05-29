from multiprocessing import freeze_support
from ImageViewer.ImageViewer import ImageViewer

def main() -> None:
    # Start the image viewer
    ImageViewer(fullScreenAllowed=True)

if __name__ == '__main__':
    freeze_support()
    main()
