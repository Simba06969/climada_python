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

Test ImpfHeatwave class.
"""

import unittest

import numpy as np

from climada.entity.impact_funcs.heat_wave import ImpfHeatwave


class TestHeatwaveDefault(unittest.TestCase):
    """Test default heatwave impact function."""

    def test_default_values(self):
        """Test default heatwave impact function creation."""
        impf = ImpfHeatwave.from_default()
        self.assertEqual(impf.name, "Default Heatwave")
        self.assertEqual(impf.haz_type, "HW")
        self.assertEqual(impf.id, 1)
        self.assertEqual(impf.intensity_unit, "°C above threshold")
        # Check intensity array
        self.assertEqual(len(impf.intensity), 31)
        self.assertEqual(impf.intensity[0], 0.0)
        self.assertEqual(impf.intensity[-1], 15.0)
        # PAA should be all ones
        self.assertTrue(np.all(impf.paa == 1.0))
        # MDD should be zero at zero intensity
        self.assertEqual(impf.mdd[0], 0.0)
        # MDD should be positive at high intensities
        self.assertGreater(impf.mdd[-1], 0.5)

    def test_custom_intensity(self):
        """Test with custom intensity array."""
        intensity = np.arange(0, 10, 1)
        impf = ImpfHeatwave.from_default(intensity=intensity)
        self.assertTrue(np.array_equal(impf.intensity, intensity))
        self.assertEqual(len(impf.mdd), len(intensity))
        self.assertEqual(len(impf.paa), len(intensity))


class TestHeatwaveSigmoid(unittest.TestCase):
    """Test sigmoid heatwave impact function."""

    def test_sigmoid_default(self):
        """Test sigmoid impact function with default parameters."""
        impf = ImpfHeatwave.from_sigmoid()
        self.assertEqual(impf.name, "Sigmoid Heatwave")
        self.assertEqual(impf.haz_type, "HW")
        self.assertEqual(impf.id, 1)
        # PAA should be all ones
        self.assertTrue(np.all(impf.paa == 1.0))
        # MDD at x0 (midpoint) should be approximately L/2
        midpoint_idx = np.argmin(np.abs(impf.intensity - 5.0))
        self.assertAlmostEqual(impf.mdd[midpoint_idx], 0.5, places=1)

    def test_sigmoid_custom_params(self):
        """Test sigmoid with custom parameters."""
        impf = ImpfHeatwave.from_sigmoid(
            impf_id=2,
            L=0.8,
            k=1.0,
            x0=3.0,
            temp_threshold=1.0,
            name="Custom Sigmoid"
        )
        self.assertEqual(impf.id, 2)
        self.assertEqual(impf.name, "Custom Sigmoid")
        # MDD below threshold should be zero
        below_threshold = impf.intensity <= 1.0
        self.assertTrue(np.all(impf.mdd[below_threshold] == 0.0))
        # Maximum MDD should approach L but not exceed it
        self.assertLessEqual(impf.mdd.max(), 0.8)

    def test_sigmoid_invalid_L(self):
        """Test that invalid L raises ValueError."""
        with self.assertRaises(ValueError):
            ImpfHeatwave.from_sigmoid(L=1.5)
        with self.assertRaises(ValueError):
            ImpfHeatwave.from_sigmoid(L=-0.1)

    def test_sigmoid_invalid_k(self):
        """Test that invalid k raises ValueError."""
        with self.assertRaises(ValueError):
            ImpfHeatwave.from_sigmoid(k=-0.5)
        with self.assertRaises(ValueError):
            ImpfHeatwave.from_sigmoid(k=0)


class TestHeatwaveStep(unittest.TestCase):
    """Test step heatwave impact function."""

    def test_step_default(self):
        """Test step impact function with default parameters."""
        impf = ImpfHeatwave.from_step()
        self.assertEqual(impf.name, "Step Heatwave")
        self.assertEqual(impf.haz_type, "HW")
        # Below threshold should be zero
        below_threshold = impf.intensity <= 3.0
        self.assertTrue(np.all(impf.mdd[below_threshold] == 0.0))
        # Above threshold should be one
        above_threshold = impf.intensity > 3.0
        self.assertTrue(np.all(impf.mdd[above_threshold] == 1.0))

    def test_step_custom_threshold(self):
        """Test step with custom threshold."""
        impf = ImpfHeatwave.from_step(temp_threshold=5.0, mdd_below=0.1, mdd_above=0.9)
        below_threshold = impf.intensity <= 5.0
        self.assertTrue(np.all(impf.mdd[below_threshold] == 0.1))
        above_threshold = impf.intensity > 5.0
        self.assertTrue(np.all(impf.mdd[above_threshold] == 0.9))

    def test_step_invalid_mdd(self):
        """Test that invalid mdd values raise ValueError."""
        with self.assertRaises(ValueError):
            ImpfHeatwave.from_step(mdd_below=-0.1)
        with self.assertRaises(ValueError):
            ImpfHeatwave.from_step(mdd_above=1.5)


class TestHeatwaveLinear(unittest.TestCase):
    """Test linear heatwave impact function."""

    def test_linear_default(self):
        """Test linear impact function with default parameters."""
        impf = ImpfHeatwave.from_linear()
        self.assertEqual(impf.name, "Linear Heatwave")
        self.assertEqual(impf.haz_type, "HW")
        # At threshold (0), MDD should be 0
        self.assertEqual(impf.mdd[0], 0.0)
        # MDD should increase linearly
        # At 5°C above threshold with slope 0.1, MDD = 0.5
        idx_5 = np.argmin(np.abs(impf.intensity - 5.0))
        self.assertAlmostEqual(impf.mdd[idx_5], 0.5, places=2)

    def test_linear_custom_slope(self):
        """Test linear with custom slope."""
        impf = ImpfHeatwave.from_linear(slope=0.2, max_mdd=0.8, temp_threshold=2.0)
        # Below threshold should be zero
        below_threshold = impf.intensity <= 2.0
        self.assertTrue(np.all(impf.mdd[below_threshold] == 0.0))
        # Check that MDD is capped at max_mdd
        self.assertLessEqual(impf.mdd.max(), 0.8)

    def test_linear_invalid_slope(self):
        """Test that invalid slope raises ValueError."""
        with self.assertRaises(ValueError):
            ImpfHeatwave.from_linear(slope=-0.1)
        with self.assertRaises(ValueError):
            ImpfHeatwave.from_linear(slope=0)

    def test_linear_invalid_max_mdd(self):
        """Test that invalid max_mdd raises ValueError."""
        with self.assertRaises(ValueError):
            ImpfHeatwave.from_linear(max_mdd=-0.1)
        with self.assertRaises(ValueError):
            ImpfHeatwave.from_linear(max_mdd=1.5)


class TestHeatwaveIntegration(unittest.TestCase):
    """Integration tests for heatwave impact functions."""

    def test_calc_mdr(self):
        """Test MDR calculation (interpolation)."""
        impf = ImpfHeatwave.from_linear(slope=0.1, temp_threshold=0.0)
        # Calculate MDR at various intensities
        mdr_0 = impf.calc_mdr(0)
        mdr_5 = impf.calc_mdr(5)
        mdr_10 = impf.calc_mdr(10)
        self.assertAlmostEqual(mdr_0, 0.0, places=5)
        self.assertAlmostEqual(mdr_5, 0.5, places=5)
        self.assertAlmostEqual(mdr_10, 1.0, places=5)

    def test_haz_type_consistency(self):
        """Test that all factory methods produce HW hazard type."""
        impf_default = ImpfHeatwave.from_default()
        impf_sigmoid = ImpfHeatwave.from_sigmoid()
        impf_step = ImpfHeatwave.from_step()
        impf_linear = ImpfHeatwave.from_linear()

        self.assertEqual(impf_default.haz_type, "HW")
        self.assertEqual(impf_sigmoid.haz_type, "HW")
        self.assertEqual(impf_step.haz_type, "HW")
        self.assertEqual(impf_linear.haz_type, "HW")


# Execute Tests
if __name__ == "__main__":
    TESTS = unittest.TestLoader().loadTestsFromTestCase(TestHeatwaveDefault)
    TESTS.addTests(unittest.TestLoader().loadTestsFromTestCase(TestHeatwaveSigmoid))
    TESTS.addTests(unittest.TestLoader().loadTestsFromTestCase(TestHeatwaveStep))
    TESTS.addTests(unittest.TestLoader().loadTestsFromTestCase(TestHeatwaveLinear))
    TESTS.addTests(unittest.TestLoader().loadTestsFromTestCase(TestHeatwaveIntegration))
    unittest.TextTestRunner(verbosity=2).run(TESTS)
