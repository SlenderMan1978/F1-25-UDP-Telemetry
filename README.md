# F1 25 Telemetry Data Collector

一个用于收集 F1 25 游戏遥测数据的 Python 工具，将实时游戏数据保存为 CSV 格式，便于数据分析和 AI 训练。


## 使用方法

### 1. 配置 F1 25 游戏

1. 启动 F1 25 游戏
2. 进入 **设置 (Settings)** → **遥测设置 (Telemetry Settings)**
3. 启用 **UDP 遥测输出 (UDP Telemetry Output)**
4. 设置 UDP 端口为 **20777**（或自定义端口）
5. 设置 UDP 发送频率（推荐：60Hz 或更高）

### 2. 运行收集器

```bash
python f1_telemetry_collector.py
```

### 3. 开始游戏

运行收集器后，开始游戏会话（练习赛、排位赛或正赛），数据将自动开始收集。

### 4. 停止收集

按 **Ctrl+C** 停止数据收集，程序会自动保存所有数据。

## 配置选项

### 修改采集频率

在 `f1_telemetry_collector.py` 文件中修改：

```python
COLLECTION_INTERVAL = 1.0  # 秒，默认每秒采集一次
```

常用设置：
- `1.0` - 每秒一次（推荐，用于一般分析）
- `0.5` - 每 0.5 秒一次（更高频率）
- `0.1` - 每 0.1 秒一次（高频率，数据量大）

### 修改 UDP 端口

```python
UDP_PORT = 20777  # 修改为游戏中设置的端口
```

### 修改输出目录

```python
collector = F1TelemetryCollector(output_dir="your_custom_directory")
```

## 输出文件

数据保存在 `f1_telemetry_data` 目录下，文件命名格式：

```
motion_20241011_143052.csv
telemetry_20241011_143052.csv
lap_data_20241011_143052.csv
car_status_20241011_143052.csv
car_damage_20241011_143052.csv
car_setups_20241011_143052.csv
session_20241011_143052.csv
motion_ex_20241011_143052.csv
```

时间戳格式：`年月日_时分秒`


## 常见问题

### Q: 程序运行后没有收到数据？

**A:** 检查以下几点：
1. F1 25 游戏是否已启动并开始会话
2. 游戏中是否启用了 UDP 遥测输出
3. UDP 端口是否匹配（游戏设置 vs 代码中的端口）
4. 防火墙是否阻止了 UDP 连接

### Q: 数据文件太大怎么办？

**A:** 
1. 增加 `COLLECTION_INTERVAL` 的值（降低采集频率）
2. 只在需要的时候运行收集器
3. 定期清理旧数据文件

### Q: 如何只收集特定类型的数据？

**A:** 在相应的解析函数中添加早期返回：

```python
def _parse_motion_packet(self, data, header):
    return  # 跳过 motion 数据收集
```

### Q: 支持其他 F1 游戏版本吗？

**A:** 此工具专为 F1 25 设计。其他版本（F1 24、F1 23 等）的数据包格式可能不同，需要调整结构体解析代码。

---

**Happy Racing! 🏎️💨**