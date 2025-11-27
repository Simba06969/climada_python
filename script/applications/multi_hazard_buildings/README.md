# Multi-Hazard Building Damage Assessment

This application demonstrates how to assess potential damage to buildings from multiple hazards
using CLIMADA. The example covers:

1. **European Winter Storms (WS)** - Available in CLIMADA core
2. **River Floods (RF)** - Available in CLIMADA Petals
3. **Heatwaves (HW)** - Available in CLIMADA Petals

## Excel Data Format

Your building data should be formatted in an Excel file with the following columns:

### Required Columns

| Column Name | Description | Example |
|-------------|-------------|---------|
| `latitude` | Latitude coordinate (decimal degrees) | 48.137154 |
| `longitude` | Longitude coordinate (decimal degrees) | 11.576124 |
| `value` | Building value in USD | 500000 |

### Optional Columns

| Column Name | Description | Example |
|-------------|-------------|---------|
| `building_name` | Name or identifier for the building | "Office Tower A" |
| `deductible` | Deductible amount for insurance | 0 |
| `cover` | Maximum covered amount | 500000 |
| `region_id` | Region identifier (e.g., country ISO code) | 276 (Germany) |
| `category_id` | Building category | 1 |
| `impf_WS` | Impact function ID for winter storms | 1 |
| `impf_RF` | Impact function ID for river floods | 1 |
| `impf_HW` | Impact function ID for heatwaves | 1 |

### Example Excel Structure

See `buildings_template.xlsx` for an example template with sample data.

## Usage

### Basic Usage

```python
from multi_hazard_assessment import MultiHazardBuildingAssessment

# Initialize assessment with your Excel file
assessment = MultiHazardBuildingAssessment("my_buildings.xlsx")

# Run assessment for all available hazards
results = assessment.run_assessment()

# Print summary
assessment.print_summary(results)

# Export results
assessment.export_results(results, "damage_results.xlsx")
```

### Using Individual Hazards

```python
# Assess only winter storm damage
ws_results = assessment.assess_winter_storm()

# Assess only river flood damage (requires CLIMADA Petals)
rf_results = assessment.assess_river_flood()

# Assess only heatwave damage (requires CLIMADA Petals)
hw_results = assessment.assess_heatwave()
```

## Requirements

### CLIMADA Core (for Winter Storms)
- climada

### CLIMADA Petals (for River Floods and Heatwaves)
- climada_petals

Install CLIMADA Petals:
```bash
pip install climada-petals
```

Or with conda:
```bash
mamba install -c conda-forge climada-petals
```

## Notes

1. **Coordinate System**: Coordinates should be in WGS84 (EPSG:4326)
2. **Value Unit**: All values should be in USD for consistency
3. **Hazard Data**: You need to provide or download hazard data for your region of interest
4. **Impact Functions**: Default impact functions are provided, but you can customize them

## Hazard-Specific Information

### European Winter Storms (WS)
- Hazard type code: "WS"
- Intensity unit: m/s (wind speed)
- Available data: WISC footprints from Copernicus Climate Data Store

### River Floods (RF)
- Hazard type code: "RF"
- Intensity unit: m (flood depth)
- Available data: ISIMIP flood data, various regional sources

### Heatwaves (HW)
- Hazard type code: "HW"
- Intensity unit: °C or degree-days
- Available data: ERA5 temperature data, regional climate models

## References

- CLIMADA documentation: https://climada-python.readthedocs.io/
- CLIMADA Petals documentation: https://climada-petals.readthedocs.io/
- WISC data: https://cds.climate.copernicus.eu/
