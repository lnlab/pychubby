"""Collection of utilities."""

import numpy as np
from skimage.draw import rectangle_perimeter
from skimage.morphology import dilation, square


def points_to_rectangle_mask(shape, top_left, bottom_right, width=1):
    """Convert two points into a rectangle boolean mask.

    Parameters
    ----------
    shape : tuple
        Represents the `(height, width)` of the final mask.

    top_left : tuple
        Two element tuple representing `(row, column)` of the top left corner of the inner rectangle.

    bottom_right : tuple
        Two element tuple representing `(row, column)` of the bottom right corner of the inner rectangle.

    width : int
        Width of the edge of the rectangle. Note that it is generated by dilation.

    Returns
    -------
    rectangle_mask : np.ndarray
        Boolean mask of shape `shape` where True entries represent the edge of the rectangle.

    Notes
    -----
    The output can be easily used for quickly visualizing a rectangle in an image. One simply does
    something like img[rectangle_mask] = 255.

    """
    if len(shape) != 2:
        raise ValueError('Only works for 2 dimensional arrays')

    rectangle_mask = np.zeros(shape, dtype=np.bool)
    rr, cc = rectangle_perimeter(top_left, bottom_right)
    rectangle_mask[rr, cc] = True
    rectangle_mask = dilation(rectangle_mask, square(width))

    return rectangle_mask