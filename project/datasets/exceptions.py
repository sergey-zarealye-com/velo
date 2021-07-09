class ImageProcessingException(Exception):
    pass


class ResolutionException(ImageProcessingException):
    pass


class ImagePlaceholderException(ImageProcessingException):
    pass
