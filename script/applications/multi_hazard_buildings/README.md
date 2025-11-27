# Multi-Hazard Building Damage Assessment

This application demonstrates how to assess potential damage to buildings from multiple hazards
using CLIMADA. The example covers:

1. **European Winter Storms (WS)** - Available in CLIMADA core
2. **River Floods (RF)** - Available in CLIMADA Petals
3. **Heatwaves (HW)** - Available in CLIMADA Petals

---

## 🚀 QUICK START: Using Your Excel File

**This is what you need to do to assess damage for buildings in your Excel file:**

### Step 1: Prepare Your Excel File

1. Open the template file `buildings_template.xlsx` (in this folder)
2. Delete the sample data rows
3. Copy & paste YOUR building data with these columns:
   - `latitude` - building latitude (e.g., 48.137154)
   - `longitude` - building longitude (e.g., 11.576124)  
   - `value` - building value in USD (e.g., 5000000)
4. Save the file (keep the name or rename it)

### Step 2: Copy This Code Into Your Jupyter Notebook

**IMPORTANT:** Change `YOUR_EXCEL_FILE.xlsx` to your actual file path!

```python
# =============================================================================
# STEP 1: IMPORTS
# =============================================================================
import pandas as pd
from climada.entity import Exposures
from climada.entity.impact_funcs import ImpactFuncSet
from climada.entity.impact_funcs.storm_europe import ImpfStormEurope
from climada.engine import ImpactCalc
from climada.util.api_client import Client

# =============================================================================
# STEP 2: LOAD YOUR BUILDINGS FROM EXCEL
# =============================================================================
# ⚠️ CHANGE THIS TO YOUR EXCEL FILE PATH!
# Examples:
#   - Same folder as notebook: "my_buildings.xlsx"
#   - Different folder: "C:/Users/YourName/Documents/my_buildings.xlsx"
#   - Mac/Linux: "/home/user/documents/my_buildings.xlsx"

EXCEL_FILE = "YOUR_EXCEL_FILE.xlsx"  # <-- CHANGE THIS!

# Read your Excel file
buildings = pd.read_excel(EXCEL_FILE, sheet_name="buildings")
print(f"✓ Loaded {len(buildings)} buildings from Excel")
print(buildings.head())  # Show first few rows

# Create CLIMADA exposures from your Excel data
exp = Exposures(
    lat=buildings['latitude'].values,
    lon=buildings['longitude'].values,
    data=buildings,
    value_unit='USD'
)
exp.gdf['impf_WS'] = 1  # Set impact function ID for winter storms
exp.check()
print(f"✓ Total building value: ${buildings['value'].sum():,.0f}")

# =============================================================================
# STEP 3: DOWNLOAD HAZARD DATA (Winter Storms for Germany)
# =============================================================================
# Change 'DEU' to your country code (e.g., 'FRA' for France, 'CHE' for Switzerland)
client = Client()
hazard_ws = client.get_hazard('storm_europe', properties={'country_iso3alpha': 'DEU'})
print(f"✓ Downloaded {hazard_ws.size} winter storm events")

# =============================================================================
# STEP 4: CALCULATE DAMAGE
# =============================================================================
# Create impact function and calculate
impf_set = ImpactFuncSet([ImpfStormEurope.from_welker(impf_id=1)])
exp.assign_centroids(hazard_ws)
impact = ImpactCalc(exp, impf_set, hazard_ws).impact()

# =============================================================================
# STEP 5: VIEW RESULTS
# =============================================================================
print(f"\n{'='*50}")
print("WINTER STORM DAMAGE ASSESSMENT RESULTS")
print('='*50)
print(f"Expected Annual Impact (total): ${impact.aai_agg:,.0f}")
print(f"Maximum single event damage:    ${impact.at_event.max():,.0f}")
print(f"\nDamage per building:")
for i in range(len(buildings)):
    name = buildings.iloc[i].get('building_name', f'Building {i+1}')
    print(f"  {name}: ${impact.eai_exp[i]:,.0f}/year")
```

### Step 3: Where to Save Your Excel File

Your Excel file can be saved **anywhere** on your computer. Just update the `EXCEL_FILE` variable:

| Location | How to write the path |
|----------|----------------------|
| Same folder as notebook | `"my_buildings.xlsx"` |
| Desktop (Windows) | `"C:/Users/YourName/Desktop/my_buildings.xlsx"` |
| Documents (Windows) | `"C:/Users/YourName/Documents/my_buildings.xlsx"` |
| Home folder (Mac) | `"/Users/YourName/my_buildings.xlsx"` |
| Home folder (Linux) | `"/home/username/my_buildings.xlsx"` |

**Tip:** Use forward slashes `/` even on Windows, or use raw strings like `r"C:\Users\..."`.

---

## Excel File Format

Your Excel file must have a sheet named **"buildings"** with these columns:

### Required Columns

| Column Name | Description | Example |
|-------------|-------------|---------|
| `latitude` | Latitude (decimal degrees) | 48.137154 |
| `longitude` | Longitude (decimal degrees) | 11.576124 |
| `value` | Building value in USD | 5000000 |

### Optional Columns

| Column Name | Description | Example |
|-------------|-------------|---------|
| `building_name` | Name/identifier | "Office Tower A" |
| `impf_WS` | Impact function ID for winter storms | 1 |
| `impf_RF` | Impact function ID for river floods | 1 |
| `impf_HW` | Impact function ID for heatwaves | 1 |

### Example Excel Content

| building_name | latitude | longitude | value |
|---------------|----------|-----------|-------|
| Office Munich | 48.137154 | 11.576124 | 5000000 |
| Factory Berlin | 52.520008 | 13.404954 | 8000000 |
| Warehouse Frankfurt | 50.110924 | 8.682127 | 15000000 |

---

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

---

## Advanced: Using the MultiHazardBuildingAssessment Class

If you prefer to use the assessment class (optional):

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

---

## Country Codes

When downloading hazard data, use ISO 3-letter country codes:

| Country | Code |
|---------|------|
| Germany | DEU |
| France | FRA |
| Switzerland | CHE |
| Austria | AUT |
| Netherlands | NLD |
| Belgium | BEL |
| United Kingdom | GBR |

---

## Requirements

- **CLIMADA Core**: Required for winter storms
- **CLIMADA Petals**: Required for river floods and heatwaves (`pip install climada-petals`)

## References

- CLIMADA documentation: https://climada-python.readthedocs.io/
- CLIMADA Petals documentation: https://climada-petals.readthedocs.io/
- CLIMADA API tutorial: https://climada-python.readthedocs.io/en/stable/tutorial/climada_util_api_client.html
