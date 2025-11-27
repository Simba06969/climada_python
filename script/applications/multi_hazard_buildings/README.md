# Multi-Hazard Building Damage Assessment

This application demonstrates how to assess potential damage to buildings from multiple hazards
using CLIMADA. The example covers:

1. **European Winter Storms (WS)** - Available in CLIMADA core
2. **River Floods (RF)** - Available in CLIMADA Petals
3. **Heatwaves (HW)** - Available in CLIMADA Petals

## Quick Start (Jupyter Notebook)

Copy and paste the following code into your Jupyter Notebook to get started:

### Step 1: Set up your building data

```python
import pandas as pd
from climada.entity import Exposures

# Option A: Create exposures directly in Python (no Excel needed)
building_data = {
    'latitude': [48.137154, 52.520008, 50.110924],  # Your building latitudes
    'longitude': [11.576124, 13.404954, 8.682127],   # Your building longitudes
    'value': [5000000, 8000000, 15000000],           # Building values in USD
    'impf_WS': [1, 1, 1],                            # Impact function ID for winter storms
    'impf_RF': [1, 1, 1],                            # Impact function ID for river floods
}

# Create exposures object
exp = Exposures(
    lat=building_data['latitude'],
    lon=building_data['longitude'],
    data=pd.DataFrame(building_data),
    value_unit='USD'
)
exp.check()
print(f"Loaded {len(exp.gdf)} buildings with total value: ${exp.gdf['value'].sum():,.0f}")
```

### Step 2: Download hazard data (using CLIMADA API)

CLIMADA provides pre-computed hazard datasets via its Data API. Here's how to download them:

```python
from climada.util.api_client import Client

# Initialize the API client
client = Client()

# List available winter storm datasets for Europe
ws_datasets = client.list_dataset_infos(data_type='storm_europe')
print("Available Winter Storm datasets:")
for ds in ws_datasets:
    print(f"  - {ds.name}: {ds.description}")

# Download a winter storm hazard for a specific country (e.g., Germany)
hazard_ws = client.get_hazard('storm_europe', properties={'country_iso3alpha': 'DEU'})
print(f"Loaded {hazard_ws.size} winter storm events")
```

### Step 3: Calculate damage (Winter Storm example)

```python
from climada.entity.impact_funcs import ImpactFuncSet
from climada.entity.impact_funcs.storm_europe import ImpfStormEurope
from climada.engine import ImpactCalc

# Create impact function for winter storms
impf_ws = ImpfStormEurope.from_welker(impf_id=1)
impf_set = ImpactFuncSet([impf_ws])

# Assign centroids (link exposures to hazard grid)
exp.assign_centroids(hazard_ws)

# Calculate impact
impact = ImpactCalc(exp, impf_set, hazard_ws).impact()

# Print results
print(f"\nResults:")
print(f"  Expected Annual Impact: ${impact.aai_agg:,.0f}")
print(f"  Max event damage: ${impact.at_event.max():,.0f}")
```

## Complete Jupyter Notebook Example

Here's a complete example you can copy into a Jupyter Notebook:

```python
# =============================================================================
# MULTI-HAZARD BUILDING DAMAGE ASSESSMENT - Complete Example
# =============================================================================

# Cell 1: Imports
import pandas as pd
import numpy as np
from climada.entity import Exposures
from climada.entity.impact_funcs import ImpactFunc, ImpactFuncSet
from climada.entity.impact_funcs.storm_europe import ImpfStormEurope
from climada.engine import ImpactCalc
from climada.util.api_client import Client

# Cell 2: Define your buildings
# Replace these with your actual building coordinates and values
buildings = pd.DataFrame({
    'building_name': ['Office Munich', 'Factory Berlin', 'Warehouse Frankfurt'],
    'latitude': [48.137154, 52.520008, 50.110924],
    'longitude': [11.576124, 13.404954, 8.682127],
    'value': [5000000, 8000000, 15000000],  # USD
    'impf_WS': [1, 1, 1],
})

# Create exposures
exp = Exposures(
    lat=buildings['latitude'].values,
    lon=buildings['longitude'].values,
    data=buildings,
    value_unit='USD',
    ref_year=2024
)
exp.check()
print(f"✓ Loaded {len(exp.gdf)} buildings")
print(f"  Total value: ${exp.gdf['value'].sum():,.0f}")

# Cell 3: Get hazard data from CLIMADA API
client = Client()

# For Winter Storms - download from API
try:
    hazard_ws = client.get_hazard('storm_europe', properties={'country_iso3alpha': 'DEU'})
    print(f"✓ Downloaded {hazard_ws.size} winter storm events for Germany")
except Exception as e:
    print(f"Note: Could not download from API: {e}")
    print("You may need to download hazard data manually (see instructions below)")

# Cell 4: Calculate Winter Storm Impact
impf_ws = ImpfStormEurope.from_welker(impf_id=1)
impf_set_ws = ImpactFuncSet([impf_ws])

exp.assign_centroids(hazard_ws)
impact_ws = ImpactCalc(exp, impf_set_ws, hazard_ws).impact()

print(f"\n=== WINTER STORM DAMAGE ASSESSMENT ===")
print(f"Expected Annual Impact (AAI): ${impact_ws.aai_agg:,.0f}")
print(f"Maximum single event damage: ${impact_ws.at_event.max():,.0f}")
print(f"\nPer-building expected annual damage:")
for i, (name, damage) in enumerate(zip(buildings['building_name'], impact_ws.eai_exp)):
    print(f"  {name}: ${damage:,.0f}")

# Cell 5: Visualize results (optional)
import matplotlib.pyplot as plt

fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Plot 1: Exposure map
exp.plot_basemap(ax=axes[0])
axes[0].set_title('Building Locations')

# Plot 2: Impact by building
axes[1].bar(buildings['building_name'], impact_ws.eai_exp)
axes[1].set_ylabel('Expected Annual Impact (USD)')
axes[1].set_title('Winter Storm Damage by Building')
axes[1].tick_params(axis='x', rotation=45)

plt.tight_layout()
plt.show()
```

## How to Obtain Hazard Data

### Option 1: CLIMADA Data API (Recommended)

CLIMADA provides pre-computed hazard data via its API:

```python
from climada.util.api_client import Client

client = Client()

# List all available hazard types
hazard_types = client.list_dataset_infos()
for h in set(ds.data_type for ds in hazard_types):
    print(h)

# Get specific hazard data
hazard = client.get_hazard('storm_europe', properties={'country_iso3alpha': 'DEU'})
```

### Option 2: River Floods (CLIMADA Petals)

```python
from climada_petals.hazard import RiverFlood

# Download river flood data for a specific region
# Note: This requires setting up CDS API credentials
rf_hazard = RiverFlood.from_isimip_yearset(
    yearset_path='path/to/isimip/data/',  # Or use download functions
    countries=['DEU'],  # ISO3 country codes
)
```

### Option 3: Download from Copernicus Climate Data Store

For WISC winter storm footprints:
1. Register at https://cds.climate.copernicus.eu/
2. Download "Winter windstorm indicators" dataset
3. Load using:

```python
from climada.hazard.storm_europe import StormEurope

hazard = StormEurope.from_footprints('/path/to/downloaded/wisc/data/')
```

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

## Using the MultiHazardBuildingAssessment Class

If you prefer to use the assessment class:

```python
import sys
sys.path.append('/path/to/script/applications/multi_hazard_buildings/')
from multi_hazard_assessment import MultiHazardBuildingAssessment

# Initialize with your Excel file
assessment = MultiHazardBuildingAssessment("my_buildings.xlsx")

# Get hazard data first
from climada.util.api_client import Client
client = Client()
hazard_ws = client.get_hazard('storm_europe', properties={'country_iso3alpha': 'DEU'})

# Run assessment
results = assessment.assess_winter_storm(hazard=hazard_ws)
assessment.print_summary({'WS': results})
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
3. **Hazard Data**: Use the CLIMADA API or download from Copernicus CDS
4. **Impact Functions**: Default impact functions are provided, but you can customize them

## Hazard-Specific Information

### European Winter Storms (WS)
- Hazard type code: "WS"
- Intensity unit: m/s (wind speed)
- Data sources:
  - CLIMADA API: `client.get_hazard('storm_europe', ...)`
  - WISC footprints: https://cds.climate.copernicus.eu/

### River Floods (RF)
- Hazard type code: "RF"
- Intensity unit: m (flood depth)
- Data sources:
  - CLIMADA Petals: `RiverFlood.from_isimip_yearset(...)`
  - ISIMIP project data

### Heatwaves (HW)
- Hazard type code: "HW"
- Intensity unit: °C or degree-days
- Data sources:
  - ERA5 temperature data
  - Regional climate models

## References

- CLIMADA documentation: https://climada-python.readthedocs.io/
- CLIMADA Petals documentation: https://climada-petals.readthedocs.io/
- CLIMADA API tutorial: https://climada-python.readthedocs.io/en/stable/tutorial/climada_util_api_client.html
- WISC data: https://cds.climate.copernicus.eu/
