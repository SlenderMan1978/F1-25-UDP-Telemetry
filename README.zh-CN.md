# F1 25 遥测数据采集器与 INI 转换器

[English](README.md) | [中文](README.zh-CN.md)

一个用于收集 F1 25 游戏遥测数据并转换为赛车模拟训练格式的 Python 工具集。支持实时数据采集和转换为 [TUMFTM/race-simulation](https://github.com/TUMFTM/race-simulation) 项目所需的 INI 格式。

## 工作流程

```
F1 25 游戏 → UDP 数据流 → CSV 文件 → INI 配置文件 → Race Simulation 训练
```

## 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

### 第一步：配置 F1 25 游戏

1. 启动 F1 25 游戏
2. 进入 **设置 (Settings)** → **遥测设置 (Telemetry Settings)**
3. 启用 **UDP 遥测输出 (UDP Telemetry Output)**
4. 设置 UDP 端口为 **20777**（或自定义端口）
5. 设置 UDP 发送频率（推荐：60Hz 或更高）

### 第二步：收集遥测数据

```bash
python f1_telemetry_collector.py
```

程序会自动监听 UDP 端口并开始收集数据。运行收集器后：

1. 开始游戏会话（练习赛、排位赛或正赛）
2. 完成至少几圈比赛以获得足够的数据
3. 按 **Ctrl+C** 停止收集

数据将保存在 `f1_telemetry_data/` 目录下。

### 第三步：转换为 INI 格式

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

### 第四步：使用 INI 文件

将生成的 INI 文件复制到 race-simulation 项目的配置目录，用于训练 VSE（Virtual Strategy Engineer）。

## 配置选项

### 数据采集配置

在 `f1_telemetry_collector.py` 中修改：

```python
COLLECTION_INTERVAL = 1.0  # 采集间隔（秒）
UDP_PORT = 20777          # UDP 端口
```

常用采集频率：
- `1.0` - 每秒一次（推荐，平衡数据量和精度）
- `0.5` - 每 0.5 秒一次（更高频率）
- `0.1` - 每 0.1 秒一次（高频率，数据量大）

### INI 转换配置

在 `f1_csv_to_ini.py` 中修改：

```python
# 修改数据源目录
converter = F1DataConverter(data_dir="your_custom_directory")

# 自定义输出文件名
converter.convert(output_filename="custom_race_config.ini")
```

## 输出文件说明

### CSV 数据文件

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

### INI 配置文件

包含以下章节：

- **[RACE_PARS]**: 比赛参数（圈数、DRS 规则等）
- **[TRACK_PARS]**: 赛道参数（圈速、超车难度、进站时间等）
- **[CAR_PARS]**: 车辆参数（燃料消耗、进站时间等）
- **[TIRESET_PARS]**: 轮胎降解参数（基于实际数据拟合）
- **[DRIVER_PARS]**: 车手参数（速度、策略、起始位置等）

## 数据分析功能

### 轮胎降解拟合

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

### 赛道参数计算

自动计算：
- `t_q`: 排位赛圈速（最快圈速）
- `t_gap_racepace`: 比赛配速与排位赛的差距
- `t_lap_sens_mass`: 燃料重量对圈速的影响
- `t_loss_pergridpos`: 每个发车位的时间损失
- `t_drseffect`: DRS 效果
- 等等...

## 常见问题

### Q: 程序运行后没有收到数据？

**A:** 检查以下几点：
1. F1 25 游戏是否已启动并开始会话
2. 游戏中是否启用了 UDP 遥测输出
3. UDP 端口是否匹配（游戏设置 vs 代码中的端口）
4. 防火墙是否阻止了 UDP 连接

### Q: 转换时提示"没有找到轮胎降解数据"？

**A:** 确保：
1. 至少完成了 3-5 圈有效圈速
2. CSV 文件中包含 `lap_data` 和 `car_status` 数据
3. 游戏中启用了完整的遥测输出
4. 尝试跑更多圈以获得更多数据点

### Q: INI 文件中的参数可以手动调整吗？

**A:** 可以！生成的 INI 文件是纯文本格式，可以使用任何文本编辑器修改。常见调整：
- 修改比赛圈数 `tot_no_laps`
- 调整轮胎降解系数
- 更改 DRS 规则
- 自定义车手策略 `strategy_info`

### Q: 数据文件太大怎么办？

**A:** 
1. 增加 `COLLECTION_INTERVAL` 的值（降低采集频率）
2. 只在需要的时候运行收集器
3. 收集完成后及时转换并删除原始 CSV 文件
4. 针对特定数据类型，可以在代码中禁用不需要的数据包解析

### Q: 支持其他 F1 游戏版本吗？

**A:** 此工具专为 F1 25 设计。其他版本（F1 24、F1 23 等）的数据包格式可能不同，需要调整结构体解析代码。主要差异在于 UDP 协议的 packet 结构定义。

### Q: 可以实时转换吗？

**A:** 当前版本采用两步流程（先收集后转换）。如需实时转换，可以修改代码在收集器中集成转换逻辑，但会增加系统负载。

---

**Happy Racing! 🏎️💨**

*For race-simulation project integration, refer to: https://github.com/TUMFTM/race-simulation*