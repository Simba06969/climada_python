"""
This file is part of CLIMADA.

Copyright (C) 2017 ETH Zurich, CLIMADA contributors listed in AUTHORS.

CLIMADA is free software: you can redistribute it and/or modify it under the
terms of the GNU General Public License as published by the Free
Software Foundation, version 3.

CLIMADA is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE.  See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along
with CLIMADA. If not, see <https://www.gnu.org/licenses/>.

---

Define impact functions for heatwaves.
"""

__all__ = ["ImpfHeatwave"]

import logging

import numpy as np

from climada.entity.impact_funcs.base import ImpactFunc

LOGGER = logging.getLogger(__name__)

# Default parameters for sigmoid impact functions
DEFAULT_SIGMOID_MIDPOINT = 5.0  # x0: Temperature at which impact = L/2
DEFAULT_SIGMOID_STEEPNESS = 0.5  # k: Steepness of the sigmoid curve


class ImpfHeatwave(ImpactFunc):
    """Impact functions for heatwaves.

    The impact is typically measured as excess mortality or morbidity
    as a function of temperature anomaly above a threshold.
    """

    def __init__(self):
        ImpactFunc.__init__(self)
        self.haz_type = "HW"

    @classmethod
    def from_default(
        cls,
        impf_id=1,
        intensity=None,
        temp_threshold=0.0,
        intensity_unit="°C above threshold",
        name="Default Heatwave",
    ):
        """
        Generate a default heatwave impact function based on a sigmoid curve.

        This function assumes that the impact increases non-linearly with
        temperature anomaly above a threshold, following common observations
        in epidemiological studies of heat-related mortality.

        Parameters
        ----------
        impf_id : int, optional
            Impact function id. Default: 1
        intensity : np.array, optional
            Intensity array (temperature anomaly in °C).
            Default: 0.5°C steps from 0 to 15°C
        temp_threshold : float, optional
            Temperature anomaly threshold below which there is no impact.
            Default: 0.0
        intensity_unit : str, optional
            Unit of the intensity. Default: "°C above threshold"
        name : str, optional
            Name of the impact function. Default: "Default Heatwave"

        Returns
        -------
        impf : ImpfHeatwave
            Heatwave impact function instance
        """
        if intensity is None:
            intensity = np.arange(0, 15.5, 0.5)

        impf = cls()
        impf.name = name
        impf.id = impf_id
        impf.intensity_unit = intensity_unit
        impf.intensity = intensity

        # PAA is 1 for all intensities (all exposed assets are affected)
        impf.paa = np.ones(intensity.shape)

        # MDD follows a sigmoid curve
        # Impact starts at threshold and increases non-linearly
        mdd = np.zeros(intensity.shape)
        above_threshold = intensity > temp_threshold
        temp_above = intensity[above_threshold] - temp_threshold
        mdd[above_threshold] = 1 / (1 + np.exp(
            -DEFAULT_SIGMOID_STEEPNESS * (temp_above - DEFAULT_SIGMOID_MIDPOINT)
        ))
        impf.mdd = mdd

        impf.check()
        return impf

    @classmethod
    def from_sigmoid(
        cls,
        impf_id=1,
        intensity=None,
        L=1.0,
        k=0.5,
        x0=5.0,
        temp_threshold=0.0,
        intensity_unit="°C above threshold",
        name="Sigmoid Heatwave",
    ):
        r"""
        Generate a sigmoid-based heatwave impact function.

        The sigmoid function is defined as:

        .. math::

           f(T) = \frac{L}{1 + e^{-k(T - x_0)}}

        for temperatures T above the threshold.

        Parameters
        ----------
        impf_id : int, optional
            Impact function id. Default: 1
        intensity : np.array, optional
            Intensity array (temperature anomaly in °C).
            Default: 0.5°C steps from 0 to 15°C
        L : float, optional
            Maximum value of the sigmoid (scales the maximum impact).
            Default: 1.0
        k : float, optional
            Steepness of the sigmoid curve. Default: 0.5
        x0 : float, optional
            Midpoint of the sigmoid (temperature at which impact = L/2).
            Default: 5.0
        temp_threshold : float, optional
            Temperature anomaly threshold below which there is no impact.
            Default: 0.0
        intensity_unit : str, optional
            Unit of the intensity. Default: "°C above threshold"
        name : str, optional
            Name of the impact function. Default: "Sigmoid Heatwave"

        Returns
        -------
        impf : ImpfHeatwave
            Heatwave impact function instance
        """
        if L < 0 or L > 1:
            raise ValueError("L must be between 0 and 1.")
        if k <= 0:
            raise ValueError("k must be positive.")

        if intensity is None:
            intensity = np.arange(0, 15.5, 0.5)

        impf = cls()
        impf.name = name
        impf.id = impf_id
        impf.intensity_unit = intensity_unit
        impf.intensity = intensity

        # PAA is 1 for all intensities
        impf.paa = np.ones(intensity.shape)

        # MDD follows a sigmoid curve
        mdd = np.zeros(intensity.shape)
        above_threshold = intensity > temp_threshold
        temp_above = intensity[above_threshold] - temp_threshold
        mdd[above_threshold] = L / (1 + np.exp(-k * (temp_above - x0)))
        impf.mdd = mdd

        impf.check()
        return impf

    @classmethod
    def from_step(
        cls,
        impf_id=1,
        intensity=None,
        temp_threshold=3.0,
        mdd_below=0.0,
        mdd_above=1.0,
        intensity_unit="°C above threshold",
        name="Step Heatwave",
    ):
        """
        Generate a step function heatwave impact function.

        The impact is zero below the threshold and constant above.
        Useful for binary impact assessments or high-resolution modeling.

        Parameters
        ----------
        impf_id : int, optional
            Impact function id. Default: 1
        intensity : np.array, optional
            Intensity array (temperature anomaly in °C).
            Default: 0.5°C steps from 0 to 15°C
        temp_threshold : float, optional
            Temperature anomaly threshold at which the step occurs.
            Default: 3.0
        mdd_below : float, optional
            Mean damage degree below the threshold. Default: 0.0
        mdd_above : float, optional
            Mean damage degree above the threshold. Default: 1.0
        intensity_unit : str, optional
            Unit of the intensity. Default: "°C above threshold"
        name : str, optional
            Name of the impact function. Default: "Step Heatwave"

        Returns
        -------
        impf : ImpfHeatwave
            Heatwave impact function instance
        """
        if mdd_below < 0 or mdd_below > 1:
            raise ValueError("mdd_below must be between 0 and 1.")
        if mdd_above < 0 or mdd_above > 1:
            raise ValueError("mdd_above must be between 0 and 1.")

        if intensity is None:
            intensity = np.arange(0, 15.5, 0.5)

        impf = cls()
        impf.name = name
        impf.id = impf_id
        impf.intensity_unit = intensity_unit
        impf.intensity = intensity

        # PAA is 1 for all intensities
        impf.paa = np.ones(intensity.shape)

        # MDD is a step function
        mdd = np.where(intensity <= temp_threshold, mdd_below, mdd_above)
        impf.mdd = mdd

        impf.check()
        return impf

    @classmethod
    def from_linear(
        cls,
        impf_id=1,
        intensity=None,
        temp_threshold=0.0,
        slope=0.1,
        max_mdd=1.0,
        intensity_unit="°C above threshold",
        name="Linear Heatwave",
    ):
        """
        Generate a linear heatwave impact function.

        The impact increases linearly with temperature above the threshold,
        capped at a maximum value.

        Parameters
        ----------
        impf_id : int, optional
            Impact function id. Default: 1
        intensity : np.array, optional
            Intensity array (temperature anomaly in °C).
            Default: 0.5°C steps from 0 to 15°C
        temp_threshold : float, optional
            Temperature anomaly threshold below which there is no impact.
            Default: 0.0
        slope : float, optional
            Rate of increase in MDD per degree above threshold.
            Default: 0.1 (10% increase per degree)
        max_mdd : float, optional
            Maximum mean damage degree. Default: 1.0
        intensity_unit : str, optional
            Unit of the intensity. Default: "°C above threshold"
        name : str, optional
            Name of the impact function. Default: "Linear Heatwave"

        Returns
        -------
        impf : ImpfHeatwave
            Heatwave impact function instance
        """
        if slope <= 0:
            raise ValueError("slope must be positive.")
        if max_mdd < 0 or max_mdd > 1:
            raise ValueError("max_mdd must be between 0 and 1.")

        if intensity is None:
            intensity = np.arange(0, 15.5, 0.5)

        impf = cls()
        impf.name = name
        impf.id = impf_id
        impf.intensity_unit = intensity_unit
        impf.intensity = intensity

        # PAA is 1 for all intensities
        impf.paa = np.ones(intensity.shape)

        # MDD increases linearly above threshold, capped at max_mdd
        mdd = np.zeros(intensity.shape)
        above_threshold = intensity > temp_threshold
        temp_above = intensity[above_threshold] - temp_threshold
        mdd[above_threshold] = np.minimum(slope * temp_above, max_mdd)
        impf.mdd = mdd

        impf.check()
        return impf
