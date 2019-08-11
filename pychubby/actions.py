"""Definition of actions."""

from abc import ABC, abstractmethod

import numpy as np
from skimage.transform import AffineTransform

from pychubby.base import DisplacementField
from pychubby.detect import LANDMARK_NAMES, LandmarkFace
from pychubby.reference import DefaultRS


class Action(ABC):
    """General Action class to be subclassed."""

    @abstractmethod
    def perform(self, lf, **kwargs):
        """Perfom action on an instance of a LandmarkFace.

        Parameters
        ----------
        lf : LandmarkFace
            Instance of a ``LandmarkFace``.

        kwargs : dict
            Action specific parameters.

        Returns
        -------
        new_lf : LandmarkFace
            Instance of a ``LandmarkFace`` after a specified action was
            taken on the input `lf`.

        """

    @staticmethod
    def pts2inst(new_points, lf, **interpolation_kwargs):
        """Generate instance of LandmarkFace via interpolation.

        Parameters
        ----------
        new_points : np.ndarray
            Array of shape `(N, 2)` representing the x and y coordinates of the
            new landmark points.

        lf : LandmarkFace
            Instance of a ``LandmarkFace`` before taking any actions.

        interpolation_kwargs : dict
            Interpolation parameters passed onto scipy.

        Returns
        -------
        new_lf : LandmarkFace
            Instance of a ``LandmarkFace`` after taking an action.

        df : DisplacementField
            Displacement field representing per pixel displacements between the
            old and new image.

        """
        if not interpolation_kwargs:
            interpolation_kwargs = {'function': 'linear'}

        df = DisplacementField.generate(lf.img.shape,
                                        lf.points,
                                        new_points,
                                        anchor_edges=True,
                                        **interpolation_kwargs)

        new_img = df.warp(lf.img)

        return LandmarkFace(new_points, new_img), df


class AbsoluteMove(Action):
    """Absolute offsets of any landmark points.

    Parameters
    ----------
    x_shifts : dict or None
        Keys are integers from 0 to 67 representing a chosen landmark points. The
        values represent the shift in the x direction to be made. If a landmark
        not specified assumed shift is 0.

    y_shifts : dict or None
        Keys are integers from 0 to 67 representing a chosen landmark points. The
        values represent the shift in the y direction to be made. If a landmark
        not specified assumed shift is 0.

    """

    def __init__(self, x_shifts=None, y_shifts=None):
        """Construct."""
        self.x_shifts = x_shifts or {}
        self.y_shifts = y_shifts or {}

    def perform(self, lf):
        """Perform absolute move.

        Specified landmarks will be shifted in either the x or y direction.

        Parameters
        ----------
        lf : LandmarkFace
            Instance of a ``LandmarkFace``.

        Returns
        -------
        new_lf : LandmarkFace
            Instance of a ``LandmarkFace`` after taking the action.

        df : DisplacementField
            Displacement field representing the transformation between the old and
            new image.

        """
        offsets = np.zeros((68, 2))

        # x shifts
        for k, v in self.x_shifts.items():
            offsets[k, 0] = v
        # y shifts
        for k, v in self.y_shifts.items():
            offsets[k, 1] = v

        new_points = lf.points + offsets

        new_lf, df = self.pts2inst(new_points, lf)

        return new_lf, df


class Lambda(Action):
    """Custom action for specifying actions with angles and norms in a reference space.

    Parameters
    ----------
    scale : float
        Absolute norm of the maximum shift. All the remaining shifts are scaled linearly.

    specs : dict
        Dictionary where keyrs represent either the index or a name of the landmark.
        The values are tuples of two elements:
            1) Angle in degrees.
            2) Proportional shift. Only the relative size towards other landmarks matters.

    reference_space : None or ReferenceSpace
        Reference space to be used.

    """

    def __init__(self, scale, specs, reference_space=None):
        """Construct."""
        self.scale = scale
        self.specs = specs
        self.reference_space = reference_space or DefaultRS()

    def perform(self, lf):
        """Perform action.

        Parameters
        ----------
        lf : LandmarkFace
            Instance of a ``LandmarkFace`` before taking the action.

        Returns
        -------
        new_lf : LandmarkFace
            Instance of a ``LandmarkFace`` after taking the action.

        df : DisplacementField
            Displacement field representing the transformation between the old and new image.

        """
        self.reference_space.estimate(lf)
        ref_points = self.reference_space.inp2ref(lf.points)

        # Create entry for AbsoluteMove
        x_shifts = {}
        y_shifts = {}

        for k, (angle, prop) in self.specs.items():
            key = k if isinstance(k, int) else LANDMARK_NAMES[k]

            ref_shift = np.array([[np.cos(np.radians(angle)), np.sin(np.radians(angle))]]) * prop * self.scale
            new_inp_point = self.reference_space.ref2inp(ref_points[key] + ref_shift)[0]
            shift = new_inp_point - lf.points[key]

            x_shifts[key] = shift[0]
            y_shifts[key] = shift[1]

        am = AbsoluteMove(x_shifts=x_shifts,
                          y_shifts=y_shifts)

        return am.perform(lf)


class Chubbify(Action):
    """Make a chubby face.

    Parameters
    ----------
    scale : float
        Absolute shift size in the reference space.

    """

    def __init__(self, scale=0.2):
        """Construct."""
        self.scale = scale

    def perform(self, lf):
        """Perform an action.

        Parameters
        ----------
        lf : LandmarkFace
            Instance of a ``LandmarkFace``.

        """
        specs = {
                 'LOWER_TEMPLE_L': (170, 0.4),
                 'LOWER_TEMPLE_R': (10, 0.4),
                 'UPPERMOST_CHEEK_L': (160, 1),
                 'UPPERMOST_CHEEK_R': (20, 1),
                 'UPPER_CHEEK_L': (150, 1),
                 'UPPER_CHEEK_R': (30, 1),
                 'LOWER_CHEEK_L': (140, 1),
                 'LOWER_CHEEK_R': (40, 1),
                 'LOWERMOST_CHEEK_L': (130, 0.8),
                 'LOWERMOST_CHEEK_R': (50, 0.8),
                 'CHIN_L': (120, 0.7),
                 'CHIN_R': (60, 0.7),
                 'CHIN': (90, 0.7)
                }

        return Lambda(self.scale, specs).perform(lf)


class LinearTransform(Action):
    """Linear transformation.

    Parameters
    ----------
    scale_x : float
        Scaling of the x axis.

    scale_y : float
        Scaling of the y axis.

    rotation : float
        Rotation in radians.

    shear : float
        Shear in radians.

    translation_x : float
        Translation in the x direction.

    translation_y : float
        Translation in the y direction.

    reference_space : None or pychubby.reference.ReferenceSpace
        Instace of the ``ReferenceSpace`` class.

    """

    def __init__(self, scale_x=1, scale_y=1, rotation=0, shear=0, translation_x=0, translation_y=0,
                 reference_space=None):
        """Construct."""
        self.scale_x = scale_x
        self.scale_y = scale_y
        self.rotation = rotation
        self.shear = shear
        self.translation_x = translation_x
        self.translation_y = translation_y
        self.reference_space = reference_space or DefaultRS()

    def perform(self, lf):
        """Perform action.

        Parameters
        ----------
        lf : LandmarkFace
            Instance of a ``LandmarkFace`` before taking the action.

        Returns
        -------
        new_lf : LandmarkFace
            Instance of a ``LandmarkFace`` after taking the action.

        df : DisplacementField
            Displacement field representing the transformation between the old and new image.

        """
        # estimate reference space
        self.reference_space.estimate(lf)

        # transform reference space landmarks
        ref_points = self.reference_space.inp2ref(lf.points)

        tform = AffineTransform(scale=(self.scale_x, self.scale_y),
                                rotation=self.rotation,
                                shear=self.shear,
                                translation=(self.translation_x, self.translation_y))
        tformed_ref_points = tform(ref_points)

        # ref2inp
        tformed_inp_points = self.reference_space.ref2inp(tformed_ref_points)

        x_shifts = {i: (tformed_inp_points[i] - lf[i])[0] for i in range(68)}
        y_shifts = {i: (tformed_inp_points[i] - lf[i])[1] for i in range(68)}

        return AbsoluteMove(x_shifts=x_shifts, y_shifts=y_shifts).perform(lf)


class OpenEyes(Action):
    """Open eyes.

    Parameters
    ----------
    scale : float
        Absolute shift size in the reference space.

    """

    def __init__(self, scale):
        """Construct."""
        self.scale = scale

    def perform(self, lf):
        """Perform action.

        Parameters
        ----------
        lf : LandmarkFace
            Instance of a ``LandmarkFace`` before taking the action.

        Returns
        -------
        new_lf : LandmarkFace
            Instance of a ``LandmarkFace`` after taking the action.

        df : DisplacementField
            Displacement field representing the transformation between the old and new image.

        """
        specs = {
                 'INNER_EYE_LID_R': (-100, 0.8),
                 'OUTER_EYE_LID_R': (-80, 1),
                 'INNER_EYE_BOTTOM_R': (100, 0.5),
                 'OUTER_EYE_BOTTOM_R': (80, 0.5),
                 'INNERMOST_EYEBROW_R': (-100, 1),
                 'INNER_EYEBROW_R': (-100, 1),
                 'MIDDLE_EYEBROW_R': (-100, 1),
                 'OUTER_EYEBROW_R': (-100, 1),
                 'OUTERMOST_EYEBROW_R': (-100, 1),
                 'INNER_EYE_LID_L': (-80, 0.8),
                 'OUTER_EYE_LID_L': (-100, 1),
                 'INNER_EYE_BOTTOM_L': (80, 0.5),
                 'OUTER_EYE_BOTTOM_L': (10, 0.5),
                 'INNERMOST_EYEBROW_L': (-80, 1),
                 'INNER_EYEBROW_L': (-80, 1),
                 'MIDDLE_EYEBROW_L': (-80, 1),
                 'OUTER_EYEBROW_L': (-80, 1),
                 'OUTERMOST_EYEBROW_L': (-80, 1)
                }
        return Lambda(self.scale, specs=specs).perform(lf)


class Smile(Action):
    """Make a smiling face.

    Parameters
    ----------
    scale : float
        Absolute shift size in the reference space.

    """

    def __init__(self, scale=0.1):
        """Construct."""
        self.scale = scale

    def perform(self, lf):
        """Perform action.

        Parameters
        ----------
        lf : LandmarkFace
            Instance of a ``LandmarkFace`` before taking the action.

        Returns
        -------
        new_lf : LandmarkFace
            Instance of a ``LandmarkFace`` after taking the action.

        df : DisplacementField
            Displacement field representing the transformation between the old and new image.

        """
        specs = {
                'OUTSIDE_MOUTH_CORNER_L': (-110, 1),
                'OUTSIDE_MOUTH_CORNER_R': (-70, 1),
                'INSIDE_MOUTH_CORNER_L': (-110, 0.8),
                'INSIDE_MOUTH_CORNER_R': (-70, 0.8),
                'OUTER_OUTSIDE_UPPER_LIP_L': (-100, 0.3),
                'OUTER_OUTSIDE_UPPER_LIP_R': (-80, 0.3),
                 }

        return Lambda(self.scale, specs).perform(lf)