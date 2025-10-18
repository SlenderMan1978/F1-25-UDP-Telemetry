# F1 25 Telemetry Data Collector & INI Converter

[English](README.md) | [中文](README.zh-CN.md)

A Python toolkit for collecting F1 25 game telemetry data and converting it to race simulation training format. Supports real-time data collection and conversion to INI format required by the [TUMFTM/race-simulation](https://github.com/TUMFTM/race-simulation) project.

## Workflow

```
F1 25 Game → UDP Data Stream → CSV Files → INI Config Files → Race Simulation Training
```

## Installation

```bash
pip install -r requirements.txt
```

## Usage Guide

### Step 1: Configure F1 25 Game

1. Launch F1 25 game
2. Go to **Settings** → **Telemetry Settings**
3. Enable **UDP Telemetry Output**
4. Set UDP port to **20777** (or custom port)
5. Set UDP send frequency (recommended: 60Hz or higher)

### Step 2: Collect Telemetry Data

```bash
python f1_telemetry_collector.py
```

The program will automatically listen to the UDP port and start collecting data. After running the collector:

1. Start a game session (Practice, Qualifying, or Race)
2. Complete at least a few laps to get sufficient data
3. Press **Ctrl+C** to stop collection

Data will be saved in the `f1_telemetry_data/` directory.

### Step 3: Convert to INI Format

After data collection, run the converter:

```bash
python f1_csv_to_ini.py
```

The converter will:
- Automatically load CSV files from `f1_telemetry_data/` directory
- Analyze tire degradation data and fit degradation curves
- Calculate track parameters (lap times, DRS effects, etc.)
- Extract driver and vehicle information
- Generate INI file with all necessary parameters

Output file naming format: `race_pars_YYYYMMDD_HHMMSS.ini`

### Step 4: Use INI File

Copy the generated INI file to the race-simulation project's configuration directory for training VSE (Virtual Strategy Engineer).

## Configuration Options

### Data Collection Configuration

Modify in `f1_telemetry_collector.py`:

```python
COLLECTION_INTERVAL = 1.0  # Collection interval (seconds)
UDP_PORT = 20777          # UDP port
```

Common collection frequencies:
- `1.0` - Once per second (recommended, balanced data volume and precision)
- `0.5` - Every 0.5 seconds (higher frequency)
- `0.1` - Every 0.1 seconds (high frequency, large data volume)

### INI Conversion Configuration

Modify in `f1_csv_to_ini.py`:

```python
# Change data source directory
converter = F1DataConverter(data_dir="your_custom_directory")

# Custom output filename
converter.convert(output_filename="custom_race_config.ini")
```

## Output Files Description

### CSV Data Files

Saved in `f1_telemetry_data/` directory, including:

| Filename | Content | Update Frequency |
|----------|---------|------------------|
| `motion_*.csv` | Vehicle position, speed, G-force | High |
| `telemetry_*.csv` | Throttle, brake, steering, RPM, etc. | High |
| `lap_data_*.csv` | Lap times, sector times, position, etc. | Per lap |
| `car_status_*.csv` | Fuel, tires, ERS status | Medium |
| `car_damage_*.csv` | Vehicle damage, tire wear | Medium |
| `car_setups_*.csv` | Vehicle setup settings | Low |
| `session_*.csv` | Session info, weather, track | Low |
| `motion_ex_*.csv` | Extended motion data (player only) | High |
| `participants_*.csv` | Participant information | Session start |
| `final_classification_*.csv` | Final classification | Session end |

### INI Configuration File

Contains the following sections:

- **[RACE_PARS]**: Race parameters (laps, DRS rules, etc.)
- **[TRACK_PARS]**: Track parameters (lap times, overtaking difficulty, pit time, etc.)
- **[CAR_PARS]**: Vehicle parameters (fuel consumption, pit time, etc.)
- **[TIRESET_PARS]**: Tire degradation parameters (fitted from actual data)
- **[DRIVER_PARS]**: Driver parameters (speed, strategy, starting position, etc.)

## Data Analysis Features

### Tire Degradation Fitting

The converter automatically:
1. Identifies different tire stints
2. Groups data by tire compound (C1-C6, I, W)
3. Fits degradation curves using linear and quadratic models
4. Removes outliers to improve fitting accuracy
5. Generates degradation coefficients: `k_0`, `k_1_lin`, `k_1_quad`, `k_2_quad`

Example output:
```
Fitting tire degradation parameters...
  ✓ HAM - A5: k_1_lin=0.0580, R²=0.892, n=15
  ✓ VER - A4: k_1_lin=0.0950, R²=0.857, n=18
```

### Track Parameter Calculation

Automatically calculates:
- `t_q`: Qualifying lap time (fastest lap)
- `t_gap_racepace`: Gap between race pace and qualifying
- `t_lap_sens_mass`: Fuel weight effect on lap time
- `t_loss_pergridpos`: Time loss per grid position
- `t_drseffect`: DRS effect
- And more...

## FAQ

### Q: Program runs but receives no data?

**A:** Check the following:
1. Is F1 25 game launched and session started?
2. Is UDP telemetry output enabled in game?
3. Does UDP port match (game settings vs code)?
4. Is firewall blocking UDP connection?

### Q: Converter says "No tire degradation data found"?

**A:** Ensure:
1. At least 3-5 valid laps completed
2. CSV files contain `lap_data` and `car_status` data
3. Full telemetry output enabled in game
4. Try running more laps to get more data points

### Q: Can INI file parameters be manually adjusted?

**A:** Yes! The generated INI file is plain text and can be edited with any text editor. Common adjustments:
- Modify race laps `tot_no_laps`
- Adjust tire degradation coefficients
- Change DRS rules
- Customize driver strategy `strategy_info`

### Q: Data files too large?

**A:** 
1. Increase `COLLECTION_INTERVAL` value (reduce collection frequency)
2. Only run collector when needed
3. Convert and delete raw CSV files promptly after collection
4. For specific data types, disable unnecessary packet parsing in code

### Q: Support for other F1 game versions?

**A:** This tool is designed for F1 25. Other versions (F1 24, F1 23, etc.) may have different packet formats and require adjustments to struct parsing code. Main differences are in UDP protocol packet structure definitions.

### Q: Real-time conversion possible?

**A:** Current version uses two-step workflow (collect then convert). For real-time conversion, you can modify code to integrate conversion logic into collector, but this increases system load.

---

**Happy Racing! 🏎️💨**

*For race-simulation project integration, refer to: https://github.com/TUMFTM/race-simulation*