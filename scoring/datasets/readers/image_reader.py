import cv2
import os
import logging


log = logging.getLogger(__name__)


def read_images(path: str, need_resize: bool):
    images, filenames = [], []

    for root, subdirs, files in os.walk(path):
        for filename in files:
            filepath = os.path.join(root, filename)
            try:
                image = cv2.imread(filepath)

                if image is not None:
                    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                    if need_resize:
                        image = cv2.resize(image, (256, 256))

                    images.append(image)
                    filenames.append(filename)
                else:
                    log.warning(f"Can't read image {filepath}")
            except Exception as err:
                log.warning(f"read_images exception: {str(err)}")

    return images, filenames
