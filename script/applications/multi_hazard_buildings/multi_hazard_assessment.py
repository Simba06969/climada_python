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

Multi-Hazard Building Damage Assessment

This module provides tools to assess potential damage to buildings from multiple
hazards including European Winter Storms, River Floods, and Heatwaves.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Union

import numpy as np
import pandas as pd

# CLIMADA core imports
from climada.entity import Exposures
from climada.entity.impact_funcs import ImpactFunc, ImpactFuncSet
from climada.entity.impact_funcs.storm_europe import ImpfStormEurope
from climada.engine import ImpactCalc
from climada.hazard import Hazard
from climada.hazard.storm_europe import StormEurope

LOGGER = logging.getLogger(__name__)


class MultiHazardBuildingAssessment:
    """
    A class for assessing building damage from multiple hazards.

    This class provides functionality to:
    1. Load building data from Excel files
    2. Define impact functions for different hazards
    3. Calculate potential damage from Winter Storms, River Floods, and Heatwaves
    4. Export results

    Attributes
    ----------
    exposures : Exposures
        CLIMADA Exposures object containing building data
    impact_funcs : dict
        Dictionary of ImpactFuncSet objects for each hazard type

    Examples
    --------
    >>> assessment = MultiHazardBuildingAssessment("my_buildings.xlsx")
    >>> results = assessment.run_assessment()
    >>> assessment.print_summary(results)
    """

    # Hazard type codes
    HAZ_TYPE_WINTER_STORM = "WS"
    HAZ_TYPE_RIVER_FLOOD = "RF"
    HAZ_TYPE_HEATWAVE = "HW"

    def __init__(
        self,
        buildings_file: Union[str, Path],
        value_unit: str = "USD",
        ref_year: int = 2024,
    ):
        """
        Initialize the multi-hazard building assessment.

        Parameters
        ----------
        buildings_file : str or Path
            Path to Excel file containing building data.
            Required columns: latitude, longitude, value
            Optional columns: building_name, deductible, cover, region_id,
                            category_id, impf_WS, impf_RF, impf_HW
        value_unit : str, optional
            Unit of the building values. Default is "USD".
        ref_year : int, optional
            Reference year for the assessment. Default is 2024.
        """
        self.buildings_file = Path(buildings_file)
        self.value_unit = value_unit
        self.ref_year = ref_year

        # Load exposures
        self.exposures = self._load_exposures()

        # Initialize impact function sets for each hazard
        self.impact_funcs = {
            self.HAZ_TYPE_WINTER_STORM: self._create_winter_storm_impact_funcs(),
            self.HAZ_TYPE_RIVER_FLOOD: self._create_river_flood_impact_funcs(),
            self.HAZ_TYPE_HEATWAVE: self._create_heatwave_impact_funcs(),
        }

        LOGGER.info(
            "Initialized MultiHazardBuildingAssessment with %d buildings",
            len(self.exposures.gdf),
        )

    def _load_exposures(self) -> Exposures:
        """
        Load building exposures from Excel file.

        Returns
        -------
        Exposures
            CLIMADA Exposures object with building data
        """
        LOGGER.info("Loading buildings from %s", self.buildings_file)

        # Read Excel file
        df = pd.read_excel(self.buildings_file, sheet_name="buildings")

        # Validate required columns
        required_cols = ["latitude", "longitude", "value"]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")

        # Rename lat/lon columns if needed
        if "lat" in df.columns and "latitude" not in df.columns:
            df = df.rename(columns={"lat": "latitude"})
        if "lon" in df.columns and "longitude" not in df.columns:
            df = df.rename(columns={"lon": "longitude"})

        # Set default impact function IDs if not provided
        for haz_type in [
            self.HAZ_TYPE_WINTER_STORM,
            self.HAZ_TYPE_RIVER_FLOOD,
            self.HAZ_TYPE_HEATWAVE,
        ]:
            col_name = f"impf_{haz_type}"
            if col_name not in df.columns:
                df[col_name] = 1

        # Create exposures
        exposures = Exposures(
            data=df,
            lat=df["latitude"].values,
            lon=df["longitude"].values,
            value=df["value"].values,
            value_unit=self.value_unit,
            ref_year=self.ref_year,
            description=f"Buildings from {self.buildings_file.name}",
        )

        exposures.check()
        return exposures

    def _create_winter_storm_impact_funcs(self) -> ImpactFuncSet:
        """
        Create impact function set for European Winter Storms.

        Returns
        -------
        ImpactFuncSet
            Impact function set for winter storm hazard
        """
        impf_set = ImpactFuncSet()

        # Use the Schwierz impact function (standard for European winter storms)
        impf_schwierz = ImpfStormEurope.from_schwierz(impf_id=1)
        impf_set.append(impf_schwierz)

        # Also add Welker calibrated function as alternative
        impf_welker = ImpfStormEurope.from_welker(impf_id=2)
        impf_set.append(impf_welker)

        return impf_set

    def _create_river_flood_impact_funcs(self) -> ImpactFuncSet:
        """
        Create impact function set for River Floods.

        This provides a simple default impact function. For more accurate
        assessments, you should use impact functions calibrated for your
        specific building types and region.

        Returns
        -------
        ImpactFuncSet
            Impact function set for river flood hazard
        """
        impf_set = ImpactFuncSet()

        # Create a generic flood impact function
        # Based on typical depth-damage curves for buildings
        impf = ImpactFunc(
            id=1,
            haz_type=self.HAZ_TYPE_RIVER_FLOOD,
            name="Generic building flood damage",
            intensity_unit="m",
            intensity=np.array([0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0, 6.0]),
            mdd=np.array([0, 0.15, 0.35, 0.50, 0.60, 0.75, 0.85, 0.95, 1.0]),
            paa=np.array([0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]),
        )
        impf_set.append(impf)

        return impf_set

    def _create_heatwave_impact_funcs(self) -> ImpactFuncSet:
        """
        Create impact function set for Heatwaves.

        This provides a simple default impact function for heat-related
        building damage (e.g., infrastructure damage, cooling costs).
        For more accurate assessments, customize for your specific
        building types and regional conditions.

        Returns
        -------
        ImpactFuncSet
            Impact function set for heatwave hazard
        """
        impf_set = ImpactFuncSet()

        # Create a generic heatwave impact function
        # Intensity is excess degrees above threshold
        impf = ImpactFunc(
            id=1,
            haz_type=self.HAZ_TYPE_HEATWAVE,
            name="Generic building heat damage",
            intensity_unit="degree-days",
            intensity=np.array([0, 10, 20, 30, 50, 75, 100, 150, 200]),
            mdd=np.array([0, 0.001, 0.005, 0.01, 0.02, 0.03, 0.05, 0.08, 0.10]),
            paa=np.array([0, 0.5, 0.7, 0.8, 0.9, 0.95, 1.0, 1.0, 1.0]),
        )
        impf_set.append(impf)

        return impf_set

    def assess_winter_storm(
        self,
        hazard: Optional[StormEurope] = None,
        hazard_file: Optional[Union[str, Path]] = None,
    ) -> Dict:
        """
        Assess building damage from European Winter Storms.

        Parameters
        ----------
        hazard : StormEurope, optional
            Pre-loaded StormEurope hazard object.
        hazard_file : str or Path, optional
            Path to hazard file (HDF5 format).

        Returns
        -------
        dict
            Dictionary containing impact results with keys:
            - 'impact': Impact object
            - 'total_damage': Total expected annual damage
            - 'damage_per_building': Per-building damage array
            - 'hazard_type': Hazard type code

        Raises
        ------
        ValueError
            If neither hazard nor hazard_file is provided.

        Notes
        -----
        Winter storm hazard data can be obtained from:
        - WISC footprints: https://cds.climate.copernicus.eu/
        - DWD ICON forecasts: via StormEurope.from_icon_grib()

        Example
        -------
        >>> # Using pre-downloaded WISC footprints
        >>> hazard = StormEurope.from_footprints("/path/to/wisc/data/")
        >>> results = assessment.assess_winter_storm(hazard=hazard)
        """
        LOGGER.info("Assessing winter storm damage...")

        if hazard is None and hazard_file is None:
            raise ValueError(
                "Please provide either a hazard object or hazard_file path.\n"
                "Winter storm hazard data can be downloaded from:\n"
                "- WISC footprints: https://cds.climate.copernicus.eu/\n"
                "  Use: hazard = StormEurope.from_footprints(path_to_data)\n"
                "- DWD ICON forecasts:\n"
                "  Use: hazard = StormEurope.from_icon_grib(run_datetime)"
            )

        if hazard is None:
            hazard = StormEurope.from_hdf5(hazard_file)

        # Assign centroids
        self.exposures.assign_centroids(hazard)

        # Calculate impact
        impact = ImpactCalc(
            exposures=self.exposures,
            impfset=self.impact_funcs[self.HAZ_TYPE_WINTER_STORM],
            hazard=hazard,
        ).impact()

        return {
            "impact": impact,
            "total_damage": impact.aai_agg,
            "damage_per_building": impact.eai_exp,
            "hazard_type": self.HAZ_TYPE_WINTER_STORM,
        }

    def assess_river_flood(
        self,
        hazard: Optional[Hazard] = None,
        hazard_file: Optional[Union[str, Path]] = None,
    ) -> Dict:
        """
        Assess building damage from River Floods.

        Parameters
        ----------
        hazard : Hazard, optional
            Pre-loaded river flood hazard object (with haz_type='RF').
        hazard_file : str or Path, optional
            Path to hazard file (HDF5 format).

        Returns
        -------
        dict
            Dictionary containing impact results.

        Notes
        -----
        River flood hazard requires CLIMADA Petals for generation.
        See: https://climada-petals.readthedocs.io/

        Available data sources:
        - ISIMIP flood data
        - JRC flood maps
        - National/regional flood hazard maps

        Example (with CLIMADA Petals)
        -----------------------------
        >>> from climada_petals.hazard import RiverFlood
        >>> hazard = RiverFlood.from_isimip(...)
        >>> results = assessment.assess_river_flood(hazard=hazard)
        """
        LOGGER.info("Assessing river flood damage...")

        if hazard is None and hazard_file is None:
            raise ValueError(
                "Please provide either a hazard object or hazard_file path.\n"
                "River flood hazard requires CLIMADA Petals:\n"
                "  pip install climada-petals\n\n"
                "Example usage:\n"
                "  from climada_petals.hazard import RiverFlood\n"
                "  hazard = RiverFlood.from_isimip(...)\n\n"
                "Or load from pre-computed file:\n"
                "  hazard = Hazard.from_hdf5('river_flood.hdf5')"
            )

        if hazard is None:
            hazard = Hazard.from_hdf5(hazard_file)

        # Verify hazard type
        if hazard.haz_type != self.HAZ_TYPE_RIVER_FLOOD:
            LOGGER.warning(
                "Hazard type is '%s', expected '%s'. Setting to RF.",
                hazard.haz_type,
                self.HAZ_TYPE_RIVER_FLOOD,
            )
            hazard.haz_type = self.HAZ_TYPE_RIVER_FLOOD

        # Assign centroids
        self.exposures.assign_centroids(hazard)

        # Calculate impact
        impact = ImpactCalc(
            exposures=self.exposures,
            impfset=self.impact_funcs[self.HAZ_TYPE_RIVER_FLOOD],
            hazard=hazard,
        ).impact()

        return {
            "impact": impact,
            "total_damage": impact.aai_agg,
            "damage_per_building": impact.eai_exp,
            "hazard_type": self.HAZ_TYPE_RIVER_FLOOD,
        }

    def assess_heatwave(
        self,
        hazard: Optional[Hazard] = None,
        hazard_file: Optional[Union[str, Path]] = None,
    ) -> Dict:
        """
        Assess building damage from Heatwaves.

        Parameters
        ----------
        hazard : Hazard, optional
            Pre-loaded heatwave hazard object (with haz_type='HW').
        hazard_file : str or Path, optional
            Path to hazard file (HDF5 format).

        Returns
        -------
        dict
            Dictionary containing impact results.

        Notes
        -----
        Heatwave hazard requires CLIMADA Petals for generation.
        See: https://climada-petals.readthedocs.io/

        Available data sources:
        - ERA5 temperature data
        - Regional climate models
        - Custom temperature datasets

        Example (with CLIMADA Petals)
        -----------------------------
        >>> from climada_petals.hazard import Heatwave
        >>> hazard = Heatwave.from_era5(...)
        >>> results = assessment.assess_heatwave(hazard=hazard)
        """
        LOGGER.info("Assessing heatwave damage...")

        if hazard is None and hazard_file is None:
            raise ValueError(
                "Please provide either a hazard object or hazard_file path.\n"
                "Heatwave hazard requires CLIMADA Petals:\n"
                "  pip install climada-petals\n\n"
                "Example usage:\n"
                "  from climada_petals.hazard import Heatwave\n"
                "  hazard = Heatwave.from_era5(...)\n\n"
                "Or load from pre-computed file:\n"
                "  hazard = Hazard.from_hdf5('heatwave.hdf5')"
            )

        if hazard is None:
            hazard = Hazard.from_hdf5(hazard_file)

        # Verify hazard type
        if hazard.haz_type != self.HAZ_TYPE_HEATWAVE:
            LOGGER.warning(
                "Hazard type is '%s', expected '%s'. Setting to HW.",
                hazard.haz_type,
                self.HAZ_TYPE_HEATWAVE,
            )
            hazard.haz_type = self.HAZ_TYPE_HEATWAVE

        # Assign centroids
        self.exposures.assign_centroids(hazard)

        # Calculate impact
        impact = ImpactCalc(
            exposures=self.exposures,
            impfset=self.impact_funcs[self.HAZ_TYPE_HEATWAVE],
            hazard=hazard,
        ).impact()

        return {
            "impact": impact,
            "total_damage": impact.aai_agg,
            "damage_per_building": impact.eai_exp,
            "hazard_type": self.HAZ_TYPE_HEATWAVE,
        }

    def run_assessment(
        self,
        hazards: Optional[Dict[str, Union[Hazard, str, Path]]] = None,
    ) -> Dict[str, Dict]:
        """
        Run damage assessment for all available hazards.

        Parameters
        ----------
        hazards : dict, optional
            Dictionary mapping hazard types to hazard objects or file paths.
            Keys should be 'WS', 'RF', or 'HW'.
            Example: {'WS': storm_hazard, 'RF': '/path/to/flood.hdf5'}

        Returns
        -------
        dict
            Dictionary of results for each hazard type that was assessed.

        Example
        -------
        >>> hazards = {
        ...     'WS': winter_storm_hazard,
        ...     'RF': river_flood_hazard,
        ... }
        >>> results = assessment.run_assessment(hazards)
        """
        if hazards is None:
            LOGGER.warning(
                "No hazards provided. Please provide hazard data to run assessment."
            )
            return {}

        results = {}

        for haz_type, haz_data in hazards.items():
            try:
                if isinstance(haz_data, (str, Path)):
                    haz_file = haz_data
                    haz_obj = None
                else:
                    haz_file = None
                    haz_obj = haz_data

                if haz_type == self.HAZ_TYPE_WINTER_STORM:
                    results[haz_type] = self.assess_winter_storm(
                        hazard=haz_obj, hazard_file=haz_file
                    )
                elif haz_type == self.HAZ_TYPE_RIVER_FLOOD:
                    results[haz_type] = self.assess_river_flood(
                        hazard=haz_obj, hazard_file=haz_file
                    )
                elif haz_type == self.HAZ_TYPE_HEATWAVE:
                    results[haz_type] = self.assess_heatwave(
                        hazard=haz_obj, hazard_file=haz_file
                    )
                else:
                    LOGGER.warning("Unknown hazard type: %s", haz_type)

            except Exception as e:
                LOGGER.error("Error assessing %s: %s", haz_type, str(e))
                results[haz_type] = {"error": str(e)}

        return results

    def print_summary(self, results: Dict[str, Dict]) -> None:
        """
        Print a summary of assessment results.

        Parameters
        ----------
        results : dict
            Results from run_assessment or individual assessment methods.
        """
        print("\n" + "=" * 60)
        print("MULTI-HAZARD BUILDING DAMAGE ASSESSMENT SUMMARY")
        print("=" * 60)
        print(f"\nNumber of buildings: {len(self.exposures.gdf)}")
        print(f"Total exposure value: {self.exposures.gdf['value'].sum():,.0f} USD")
        print(f"Reference year: {self.ref_year}")

        total_aai = 0

        for haz_type, result in results.items():
            print(f"\n{'-' * 40}")
            hazard_name = {
                "WS": "Winter Storm",
                "RF": "River Flood",
                "HW": "Heatwave",
            }.get(haz_type, haz_type)

            print(f"Hazard: {hazard_name} ({haz_type})")

            if "error" in result:
                print(f"  Error: {result['error']}")
            else:
                aai = result["total_damage"]
                total_aai += aai
                print(f"  Expected Annual Impact (AAI): {aai:,.0f} USD")
                print(f"  Max damage per building: {result['damage_per_building'].max():,.0f} USD")
                print(f"  Buildings affected: {np.sum(result['damage_per_building'] > 0)}")

        print(f"\n{'=' * 60}")
        print(f"TOTAL EXPECTED ANNUAL IMPACT: {total_aai:,.0f} USD")
        print("=" * 60 + "\n")

    def export_results(
        self,
        results: Dict[str, Dict],
        output_file: Union[str, Path],
    ) -> None:
        """
        Export assessment results to Excel file.

        Parameters
        ----------
        results : dict
            Results from run_assessment or individual assessment methods.
        output_file : str or Path
            Path to output Excel file.
        """
        output_file = Path(output_file)

        # Create summary dataframe
        summary_data = []
        for haz_type, result in results.items():
            if "error" not in result:
                summary_data.append({
                    "hazard_type": haz_type,
                    "expected_annual_impact": result["total_damage"],
                    "max_building_damage": result["damage_per_building"].max(),
                    "buildings_affected": np.sum(result["damage_per_building"] > 0),
                })

        summary_df = pd.DataFrame(summary_data)

        # Create per-building results
        building_results = self.exposures.gdf.copy()
        for haz_type, result in results.items():
            if "error" not in result:
                building_results[f"damage_{haz_type}"] = result["damage_per_building"]

        # Write to Excel
        with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
            summary_df.to_excel(writer, sheet_name="summary", index=False)
            building_results.to_excel(writer, sheet_name="building_damage", index=False)

        LOGGER.info("Results exported to %s", output_file)


def create_sample_exposures(output_file: Union[str, Path] = "sample_buildings.xlsx"):
    """
    Create a sample exposures Excel file for testing.

    Parameters
    ----------
    output_file : str or Path
        Path to output Excel file.
    """
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill

    # Sample data for European cities
    data = {
        "building_name": [
            "Munich Office Tower",
            "Berlin Industrial Park",
            "Vienna Shopping Mall",
            "Zurich Headquarters",
            "Frankfurt Data Center",
        ],
        "latitude": [48.137154, 52.520008, 48.210033, 47.376887, 50.110924],
        "longitude": [11.576124, 13.404954, 16.363449, 8.541694, 8.682127],
        "value": [10000000, 25000000, 15000000, 50000000, 30000000],
        "deductible": [0, 0, 0, 0, 0],
        "cover": [10000000, 25000000, 15000000, 50000000, 30000000],
        "region_id": [276, 276, 40, 756, 276],
        "category_id": [1, 2, 1, 1, 2],
        "impf_WS": [1, 1, 1, 1, 1],
        "impf_RF": [1, 1, 1, 1, 1],
        "impf_HW": [1, 1, 1, 1, 1],
    }

    df = pd.DataFrame(data)

    wb = Workbook()
    ws = wb.active
    ws.title = "buildings"

    # Header style
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")

    # Write headers
    for col, header in enumerate(df.columns, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill

    # Write data
    for r_idx, row in df.iterrows():
        for c_idx, value in enumerate(row.values, 1):
            ws.cell(row=r_idx + 2, column=c_idx, value=value)

    wb.save(output_file)
    print(f"Sample exposures file created: {output_file}")


if __name__ == "__main__":
    # Example usage demonstration
    import sys

    print("Multi-Hazard Building Damage Assessment Tool")
    print("=" * 50)
    print()
    print("This tool assesses building damage from:")
    print("  - European Winter Storms (WS)")
    print("  - River Floods (RF) - requires CLIMADA Petals")
    print("  - Heatwaves (HW) - requires CLIMADA Petals")
    print()
    print("Usage:")
    print("  1. Create your buildings Excel file using buildings_template.xlsx")
    print("  2. Import this module in your Python script:")
    print()
    print("     from multi_hazard_assessment import MultiHazardBuildingAssessment")
    print()
    print("  3. Initialize and run assessment:")
    print()
    print("     assessment = MultiHazardBuildingAssessment('my_buildings.xlsx')")
    print("     results = assessment.assess_winter_storm(hazard=my_hazard)")
    print("     assessment.print_summary(results)")
    print()
    print("For detailed documentation, see README.md")
    print()

    # Create sample file if requested
    if len(sys.argv) > 1 and sys.argv[1] == "--create-sample":
        create_sample_exposures()
