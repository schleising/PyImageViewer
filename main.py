from pathlib import Path
import sys

from ImageViewer.ImageViewer import ImageViewer

def main() -> None:
    if len(sys.argv) > 1:
        imagePath = Path(sys.argv[1])
    else:
        imagePath = Path.home() / 'Pictures/test images'

    ImageViewer(imagePath)

if __name__ == '__main__':
    main()
