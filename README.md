# F1 25 Telemetry Data Collector & INI Converter

<div align="right">
  <a href="#" onclick="showLanguage('en'); return false;">English</a> | 
  <a href="#" onclick="showLanguage('zh'); return false;">中文</a>
</div>

<div id="lang-en" style="display:none;">

## English Version

A Python toolkit for collecting F1 25 game telemetry data and converting it to race simulation training format. Supports real-time data collection and conversion to INI format required by the [TUMFTM/race-simulation](https://github.com/TUMFTM/race-simulation) project.

### Workflow

```
F1 25 Game → UDP Data Stream → CSV Files → INI Config Files → Race Simulation Training
```

### Installation

```bash
pip install -r requirements.txt
```

### Usage Guide

#### Step 1: Configure F1 25 Game

1. Launch F1 25 game
2. Go to **Settings** → **Telemetry Settings**
3. Enable **UDP Telemetry Output**
4. Set UDP port to **20777** (or custom port)
5. Set UDP send frequency (recommended: 60Hz or higher)

#### Step 2: Collect Telemetry Data

```bash
python f1_telemetry_collector.py
```

The program will automatically listen to the UDP port and start collecting data. After running the collector:

1. Start a game session (Practice, Qualifying, or Race)
2. Complete at least a few laps to get sufficient data
3. Press **Ctrl+C** to stop collection

Data will be saved in the `f1_telemetry_data/` directory.

#### Step 3: Convert to INI Format

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

#### Step 4: Use INI File

Copy the generated INI file to the race-simulation project's configuration directory for training VSE (Virtual Strategy Engineer).

### Configuration Options

#### Data Collection Configuration

Modify in `f1_telemetry_collector.py`:

```python
COLLECTION_INTERVAL = 1.0  # Collection interval (seconds)
UDP_PORT = 20777          # UDP port
```

Common collection frequencies:
- `1.0` - Once per second (recommended, balanced data volume and precision)
- `0.5` - Every 0.5 seconds (higher frequency)
- `0.1` - Every 0.1 seconds (high frequency, large data volume)

#### INI Conversion Configuration

Modify in `f1_csv_to_ini.py`:

```python
# Change data source directory
converter = F1DataConverter(data_dir="your_custom_directory")

# Custom output filename
converter.convert(output_filename="custom_race_config.ini")
```

### Output Files Description

#### CSV Data Files

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

#### INI Configuration File

Contains the following sections:

- **[RACE_PARS]**: Race parameters (laps, DRS rules, etc.)
- **[TRACK_PARS]**: Track parameters (lap times, overtaking difficulty, pit time, etc.)
- **[CAR_PARS]**: Vehicle parameters (fuel consumption, pit time, etc.)
- **[TIRESET_PARS]**: Tire degradation parameters (fitted from actual data)
- **[DRIVER_PARS]**: Driver parameters (speed, strategy, starting position, etc.)

### Data Analysis Features

#### Tire Degradation Fitting

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

#### Track Parameter Calculation

Automatically calculates:
- `t_q`: Qualifying lap time (fastest lap)
- `t_gap_racepace`: Gap between race pace and qualifying
- `t_lap_sens_mass`: Fuel weight effect on lap time
- `t_loss_pergridpos`: Time loss per grid position
- `t_drseffect`: DRS effect
- And more...

### FAQ

#### Q: Program runs but receives no data?

**A:** Check the following:
1. Is F1 25 game launched and session started?
2. Is UDP telemetry output enabled in game?
3. Does UDP port match (game settings vs code)?
4. Is firewall blocking UDP connection?

#### Q: Converter says "No tire degradation data found"?

**A:** Ensure:
1. At least 3-5 valid laps completed
2. CSV files contain `lap_data` and `car_status` data
3. Full telemetry output enabled in game
4. Try running more laps to get more data points

#### Q: Can INI file parameters be manually adjusted?

**A:** Yes! The generated INI file is plain text and can be edited with any text editor. Common adjustments:
- Modify race laps `tot_no_laps`
- Adjust tire degradation coefficients
- Change DRS rules
- Customize driver strategy `strategy_info`

#### Q: Data files too large?

**A:** 
1. Increase `COLLECTION_INTERVAL` value (reduce collection frequency)
2. Only run collector when needed
3. Convert and delete raw CSV files promptly after collection
4. For specific data types, disable unnecessary packet parsing in code

#### Q: Support for other F1 game versions?

**A:** This tool is designed for F1 25. Other versions (F1 24, F1 23, etc.) may have different packet formats and require adjustments to struct parsing code. Main differences are in UDP protocol packet structure definitions.

#### Q: Real-time conversion possible?

**A:** Current version uses two-step workflow (collect then convert). For real-time conversion, you can modify code to integrate conversion logic into collector, but this increases system load.

---

**Happy Racing! 🏎️💨**

*For race-simulation project integration, refer to: https://github.com/TUMFTM/race-simulation*

</div>

<div id="lang-zh">

## 中文版本

一个用于收集 F1 25 游戏遥测数据并转换为赛车模拟训练格式的 Python 工具集。支持实时数据采集和转换为 [TUMFTM/race-simulation](https://github.com/TUMFTM/race-simulation) 项目所需的 INI 格式。

### 工作流程

```
F1 25 游戏 → UDP 数据流 → CSV 文件 → INI 配置文件 → Race Simulation 训练
```

### 安装依赖

```bash
pip install -r requirements.txt
```

### 使用方法

#### 第一步：配置 F1 25 游戏

1. 启动 F1 25 游戏
2. 进入 **设置 (Settings)** → **遥测设置 (Telemetry Settings)**
3. 启用 **UDP 遥测输出 (UDP Telemetry Output)**
4. 设置 UDP 端口为 **20777**（或自定义端口）
5. 设置 UDP 发送频率（推荐：60Hz 或更高）

#### 第二步：收集遥测数据

```bash
python f1_telemetry_collector.py
```

程序会自动监听 UDP 端口并开始收集数据。运行收集器后：

1. 开始游戏会话（练习赛、排位赛或正赛）
2. 完成至少几圈比赛以获得足够的数据
3. 按 **Ctrl+C** 停止收集

数据将保存在 `f1_telemetry_data/` 目录下。

#### 第三步：转换为 INI 格式

数据收集完成后，运行转换器：

```bash
python f1_csv_to_ini.py
```

转换器会：
- 自动加载 `f1_telemetry_data/` 目录中的 CSV 文件
- 分析轮胎降解数据并拟合降解曲线
- 计算赛道参数（圈速、DRS 效果等）
- 提取车手和车辆信息
- 生成包含所有必要参数的 INI 文件

输出文件命名格式：`race_pars_YYYYMMDD_HHMMSS.ini`

#### 第四步：使用 INI 文件

将生成的 INI 文件复制到 race-simulation 项目的配置目录，用于训练 VSE（Virtual Strategy Engineer）。

### 配置选项

#### 数据采集配置

在 `f1_telemetry_collector.py` 中修改：

```python
COLLECTION_INTERVAL = 1.0  # 采集间隔（秒）
UDP_PORT = 20777          # UDP 端口
```

常用采集频率：
- `1.0` - 每秒一次（推荐，平衡数据量和精度）
- `0.5` - 每 0.5 秒一次（更高频率）
- `0.1` - 每 0.1 秒一次（高频率，数据量大）

#### INI 转换配置

在 `f1_csv_to_ini.py` 中修改：

```python
# 修改数据源目录
converter = F1DataConverter(data_dir="your_custom_directory")

# 自定义输出文件名
converter.convert(output_filename="custom_race_config.ini")
```

### 输出文件说明

#### CSV 数据文件

保存在 `f1_telemetry_data/` 目录，包含：

| 文件名 | 内容 | 更新频率 |
|--------|------|----------|
| `motion_*.csv` | 车辆位置、速度、G 力 | 高频 |
| `telemetry_*.csv` | 油门、刹车、转向、引擎转速等 | 高频 |
| `lap_data_*.csv` | 圈速、扇区时间、位置等 | 每圈 |
| `car_status_*.csv` | 燃料、轮胎、ERS 状态 | 中频 |
| `car_damage_*.csv` | 车辆损伤、轮胎磨损 | 中频 |
| `car_setups_*.csv` | 车辆调校设置 | 低频 |
| `session_*.csv` | 赛事信息、天气、赛道 | 低频 |
| `motion_ex_*.csv` | 扩展运动数据（仅玩家） | 高频 |
| `participants_*.csv` | 参赛者信息 | 会话开始 |
| `final_classification_*.csv` | 最终排名 | 会话结束 |

#### INI 配置文件

包含以下章节：

- **[RACE_PARS]**: 比赛参数（圈数、DRS 规则等）
- **[TRACK_PARS]**: 赛道参数（圈速、超车难度、进站时间等）
- **[CAR_PARS]**: 车辆参数（燃料消耗、进站时间等）
- **[TIRESET_PARS]**: 轮胎降解参数（基于实际数据拟合）
- **[DRIVER_PARS]**: 车手参数（速度、策略、起始位置等）

### 数据分析功能

#### 轮胎降解拟合

转换器会自动：
1. 识别不同的轮胎 stint（使用周期）
2. 按轮胎配方（C1-C6、I、W）分组数据
3. 使用线性和二次模型拟合降解曲线
4. 移除异常值以提高拟合精度
5. 生成降解系数：`k_0`, `k_1_lin`, `k_1_quad`, `k_2_quad`

输出示例：
```
拟合轮胎降解参数...
  ✓ HAM - A5: k_1_lin=0.0580, R²=0.892, n=15
  ✓ VER - A4: k_1_lin=0.0950, R²=0.857, n=18
```

#### 赛道参数计算

自动计算：
- `t_q`: 排位赛圈速（最快圈速）
- `t_gap_racepace`: 比赛配速与排位赛的差距
- `t_lap_sens_mass`: 燃料重量对圈速的影响
- `t_loss_pergridpos`: 每个发车位的时间损失
- `t_drseffect`: DRS 效果
- 等等...

### 常见问题

#### Q: 程序运行后没有收到数据？

**A:** 检查以下几点：
1. F1 25 游戏是否已启动并开始会话
2. 游戏中是否启用了 UDP 遥测输出
3. UDP 端口是否匹配（游戏设置 vs 代码中的端口）
4. 防火墙是否阻止了 UDP 连接

#### Q: 转换时提示"没有找到轮胎降解数据"？

**A:** 确保：
1. 至少完成了 3-5 圈有效圈速
2. CSV 文件中包含 `lap_data` 和 `car_status` 数据
3. 游戏中启用了完整的遥测输出
4. 尝试跑更多圈以获得更多数据点

#### Q: INI 文件中的参数可以手动调整吗？

**A:** 可以！生成的 INI 文件是纯文本格式，可以使用任何文本编辑器修改。常见调整：
- 修改比赛圈数 `tot_no_laps`
- 调整轮胎降解系数
- 更改 DRS 规则
- 自定义车手策略 `strategy_info`

#### Q: 数据文件太大怎么办？

**A:** 
1. 增加 `COLLECTION_INTERVAL` 的值（降低采集频率）
2. 只在需要的时候运行收集器
3. 收集完成后及时转换并删除原始 CSV 文件
4. 针对特定数据类型，可以在代码中禁用不需要的数据包解析

#### Q: 支持其他 F1 游戏版本吗？

**A:** 此工具专为 F1 25 设计。其他版本（F1 24、F1 23 等）的数据包格式可能不同，需要调整结构体解析代码。主要差异在于 UDP 协议的 packet 结构定义。

#### Q: 可以实时转换吗？

**A:** 当前版本采用两步流程（先收集后转换）。如需实时转换，可以修改代码在收集器中集成转换逻辑，但会增加系统负载。

---

**Happy Racing! 🏎️💨**

*For race-simulation project integration, refer to: https://github.com/TUMFTM/race-simulation*

</div>

<script>
function showLanguage(lang) {
  const enDiv = document.getElementById('lang-en');
  const zhDiv = document.getElementById('lang-zh');
  
  if (lang === 'en') {
    enDiv.style.display = 'block';
    zhDiv.style.display = 'none';
  } else {
    enDiv.style.display = 'none';
    zhDiv.style.display = 'block';
  }
}

// Default to Chinese
document.addEventListener('DOMContentLoaded', function() {
  showLanguage('zh');
});
</script>
