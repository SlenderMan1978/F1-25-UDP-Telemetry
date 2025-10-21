"""
F1 25 CSV Telemetry Data to INI Converter (Enhanced with Optimal Strategy)
将F1 25游戏收集的CSV遥测数据转换为race simulation所需的.ini格式
包含完整的track_pars, MONTE_CARLO_PARS, EVENT_PARS和VSE_PARS
新增:理论最优换胎策略计算
"""

import pandas as pd
import numpy as np
from scipy.optimize import curve_fit
from scipy import stats
import os
import json
from collections import defaultdict
from datetime import datetime

# 自定义JSON编码器,处理numpy/pandas类型
class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64, np.float32)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)

# 轮胎化合物映射 (使用 visual_tyre_compound - 根据F1 25 UDP规范)
VISUAL_TYRE_COMPOUND_MAP = {
    16: "A3",  # Soft
    17: "A4",  # Medium
    18: "A6",  # Hard
    7: "I",    # Intermediate
    8: "W"     # Wet
}

# 实际轮胎化合物映射 (用于参考,但不在主逻辑中使用)
ACTUAL_TYRE_COMPOUND_MAP = {
    16: "C5", 17: "C4", 18: "C3", 19: "C2", 20: "C1",
    21: "C0", 22: "C6", 7: "I", 8: "W"
}

# 车队ID映射
TEAM_ID_MAP = {
    0: "Mercedes", 1: "Ferrari", 2: "RedBull", 3: "Williams",
    4: "AstonMartin", 5: "Alpine", 6: "RB", 7: "Haas",
    8: "McLaren", 9: "Sauber"
}

# 赛道ID映射
TRACK_ID_MAP = {
    0: "Melbourne", 2: "Shanghai", 3: "Bahrain", 4: "Catalunya",
    5: "Monaco", 6: "Montreal", 7: "Silverstone", 9: "Hungaroring",
    10: "Spa", 11: "Monza", 12: "Singapore", 13: "Suzuka",
    14: "AbuDhabi", 15: "Texas", 16: "Brazil", 17: "Austria",
    19: "Mexico", 20: "Baku", 26: "Zandvoort", 27: "Imola",
    29: "Jeddah", 30: "Miami", 31: "LasVegas", 32: "Losail"
}

# Driver ID映射表
DRIVER_ID_MAP = {
    0: "Carlos Sainz", 2: "Daniel Ricciardo", 3: "Fernando Alonso",
    4: "Felipe Massa", 7: "Lewis Hamilton", 9: "Max Verstappen",
    10: "Nico Hülkenburg", 11: "Kevin Magnussen", 14: "Sergio Pérez",
    15: "Valtteri Bottas", 17: "Esteban Ocon", 19: "Lance Stroll",
    20: "Arron Barnes", 21: "Martin Giles", 22: "Alex Murray",
    23: "Lucas Roth", 24: "Igor Correia", 25: "Sophie Levasseur",
    26: "Jonas Schiffer", 27: "Alain Forest", 28: "Jay Letourneau",
    29: "Esto Saari", 30: "Yasar Atiyeh", 31: "Callisto Calabresi",
    32: "Naota Izumi", 33: "Howard Clarke", 34: "Lars Kaufmann",
    35: "Marie Laursen", 36: "Flavio Nieves", 38: "Klimek Michalski",
    39: "Santiago Moreno", 40: "Benjamin Coppens", 41: "Noah Visser",
    50: "George Russell", 54: "Lando Norris", 58: "Charles Leclerc",
    59: "Pierre Gasly", 62: "Alexander Albon", 70: "Rashid Nair",
    71: "Jack Tremblay", 77: "Ayrton Senna", 80: "Guanyu Zhou",
    83: "Juan Manuel Correa", 90: "Michael Schumacher", 94: "Yuki Tsunoda",
    102: "Aidan Jackson", 109: "Jenson Button", 110: "David Coulthard",
    112: "Oscar Piastri", 113: "Liam Lawson", 116: "Richard Verschoor",
    123: "Enzo Fittipaldi", 125: "Mark Webber", 126: "Jacques Villeneuve",
    127: "Callie Mayer", 132: "Logan Sargeant", 136: "Jack Doohan",
    137: "Amaury Cordeel", 138: "Dennis Hauger", 145: "Zane Maloney",
    146: "Victor Martins", 147: "Oliver Bearman", 148: "Jak Crawford",
    149: "Isack Hadjar", 152: "Roman Stanek", 153: "Kush Maini",
    156: "Brendon Leigh", 157: "David Tonizza", 158: "Jarno Opmeer",
    159: "Lucas Blakeley", 160: "Paul Aron", 161: "Gabriel Bortoleto",
    162: "Franco Colapinto", 163: "Taylor Barnard", 164: "Joshua Dürksen",
    165: "Andrea-Kimi Antonelli", 166: "Ritomo Miyata", 167: "Rafael Villagómez",
    168: "Zak O'Sullivan", 169: "Pepe Marti", 170: "Sonny Hayes",
    171: "Joshua Pearce", 172: "Callum Voisin", 173: "Matias Zagazeta",
    174: "Nikola Tsolov", 175: "Tim Tramnitz", 185: "Luca Cortez"
}

class F1DataConverter:
    def __init__(self, data_dir="f1_telemetry_data"):
        self.data_dir = data_dir
        self.session_data = {}
        self.participants = {}
        self.driver_lap_times = defaultdict(list)
        self.tyre_degradation_data = defaultdict(lambda: defaultdict(list))
        self.pit_stop_data = defaultdict(list)
        self.fcy_phases = []
        self.retirements = []
        self.driver_strategies = defaultdict(list)

    def load_csv_files(self):
        """加载所有CSV文件"""
        print("正在加载CSV文件...")

        csv_files = {
            'session': None, 'participants': None, 'lap_data': None,
            'telemetry': None, 'car_status': None, 'car_damage': None,
            'car_setups': None, 'final_classification': None
        }

        for filename in os.listdir(self.data_dir):
            if not filename.endswith('.csv'):
                continue

            for key in csv_files.keys():
                if filename.startswith(key):
                    filepath = os.path.join(self.data_dir, filename)
                    try:
                        df = pd.read_csv(filepath, index_col=False)
                        csv_files[key] = df
                        print(f"  ✓ 加载 {filename}: {len(df)} 行")
                    except Exception as e:
                        print(f"  ✗ 加载 {filename} 失败: {e}")

        return csv_files

    def extract_session_info(self, session_df):
        """提取赛事基本信息"""
        if session_df is None or len(session_df) == 0:
            return None

        row = session_df.iloc[0]

        return {
            'track_id': int(row.get('track_id', -1)),
            'track_name': TRACK_ID_MAP.get(int(row.get('track_id', -1)), "Unknown"),
            'total_laps': int(row.get('total_laps', 0)),
            'track_length': int(row.get('track_length', 0)),
            'session_type': int(row.get('session_type', 0)),
            'formula': int(row.get('formula', 0)),
            'pit_speed_limit': int(row.get('pit_speed_limit', 0))
        }

    def extract_participants_info(self, participants_df):
        """提取参赛者信息 - 使用driver_id映射姓名"""
        if participants_df is None or len(participants_df) == 0:
            return {}

        print("\n提取参赛者信息...")
        participants = {}

        # 获取每个car_index的最新记录
        for car_idx in participants_df['car_index'].unique():
            car_data = participants_df[participants_df['car_index'] == car_idx].iloc[-1]

            team_id = int(car_data.get('team_id', 255))
            driver_id = int(car_data.get('driver_id', 255))

            # 跳过无效的车辆索引
            if team_id == 255 or driver_id == 255:
                continue

            driver_name = DRIVER_ID_MAP.get(driver_id, f'Driver_{car_idx}')

            participants[int(car_idx)] = {
                'name': driver_name,
                'driver_id': driver_id,
                'team_id': team_id,
                'team': TEAM_ID_MAP.get(team_id, f"Team_{team_id}"),
                'race_number': int(car_data.get('race_number', 0)),
                'ai_controlled': int(car_data.get('ai_controlled', 1))
            }

        print(f"  找到 {len(participants)} 位参赛者")
        for idx, info in participants.items():
            print(f"    车辆{idx}: {info['name']} ({info['team']}) [Driver ID: {info['driver_id']}]")

        return participants

    def analyze_lap_times(self, lap_data_df):
        """分析圈速数据"""
        if lap_data_df is None or len(lap_data_df) == 0:
            return

        print("\n分析圈速数据...")

        for car_idx in lap_data_df['car_index'].unique():
            car_laps = lap_data_df[lap_data_df['car_index'] == car_idx]

            # 提取有效圈速
            valid_laps = car_laps[
                (car_laps['last_lap_time_ms'] > 0) &
                (car_laps['current_lap_invalid'] == 0)
            ]

            for _, lap in valid_laps.iterrows():
                self.driver_lap_times[car_idx].append({
                    'lap_num': int(lap['current_lap_num']),
                    'lap_time_ms': int(lap['last_lap_time_ms']),
                    'lap_time_s': lap['last_lap_time_ms'] / 1000.0
                })

    def analyze_pit_stops(self, lap_data_df):
        """分析进站数据 - 用于计算进出站时间损失"""
        if lap_data_df is None or len(lap_data_df) == 0:
            return

        print("\n分析进站数据...")

        for car_idx in lap_data_df['car_index'].unique():
            car_data = lap_data_df[lap_data_df['car_index'] == car_idx].copy()
            car_data = car_data.sort_values('current_lap_num')

            # 检测进站:pit_status从0变为非0
            car_data['pit_entry'] = (car_data['pit_status'] > 0) & (car_data['pit_status'].shift(1) == 0)
            car_data['pit_exit'] = (car_data['pit_status'] == 0) & (car_data['pit_status'].shift(1) > 0)

            pit_entries = car_data[car_data['pit_entry']]
            pit_exits = car_data[car_data['pit_exit']]

            for _, entry in pit_entries.iterrows():
                lap_num = int(entry['current_lap_num'])

                # 查找对应的出站
                exit_lap = pit_exits[pit_exits['current_lap_num'] >= lap_num]
                if len(exit_lap) > 0:
                    exit_lap = exit_lap.iloc[0]

                    # 计算进出站时间损失(相对于正常圈速)
                    normal_lap_times = car_data[
                        (car_data['last_lap_time_ms'] > 0) &
                        (car_data['pit_status'] == 0) &
                        (car_data['current_lap_invalid'] == 0)
                    ]['last_lap_time_ms']

                    if len(normal_lap_times) > 0:
                        avg_normal_lap = normal_lap_times.median() / 1000.0
                        inlap_time = entry['last_lap_time_ms'] / 1000.0 if entry['last_lap_time_ms'] > 0 else avg_normal_lap
                        outlap_time = exit_lap['last_lap_time_ms'] / 1000.0 if exit_lap['last_lap_time_ms'] > 0 else avg_normal_lap

                        self.pit_stop_data[car_idx].append({
                            'lap_num': lap_num,
                            'inlap_loss': max(0, inlap_time - avg_normal_lap),
                            'outlap_loss': max(0, outlap_time - avg_normal_lap)
                        })

        # 打印统计
        total_stops = sum(len(stops) for stops in self.pit_stop_data.values())
        print(f"  找到 {total_stops} 次进站")

    def analyze_fcy_phases(self, session_df, lap_data_df):
        """分析FCY(安全车/VSC)阶段"""
        if session_df is None or len(session_df) == 0:
            return

        print("\n分析FCY阶段...")

        session_df = session_df.copy()
        session_df = session_df.sort_values('timestamp')

        # 检测安全车状态变化 (0=无, 1=全场, 2=虚拟, 3=编队圈)
        session_df['sc_change'] = session_df['safety_car_status'].ne(session_df['safety_car_status'].shift())

        fcy_start = None
        fcy_type = None

        for _, row in session_df[session_df['sc_change']].iterrows():
            sc_status = int(row['safety_car_status'])

            if sc_status in [1, 2] and fcy_start is None:  # FCY开始
                fcy_start = row['timestamp']
                fcy_type = "SC" if sc_status == 1 else "VSC"

            elif sc_status == 0 and fcy_start is not None:  # FCY结束
                self.fcy_phases.append({
                    'start_time': fcy_start,
                    'end_time': row['timestamp'],
                    'type': fcy_type,
                    'duration': row['timestamp'] - fcy_start
                })
                fcy_start = None
                fcy_type = None

        print(f"  找到 {len(self.fcy_phases)} 个FCY阶段")
        for phase in self.fcy_phases:
            print(f"    {phase['type']}: {phase['start_time']:.1f}s - {phase['end_time']:.1f}s")

    def analyze_retirements(self, lap_data_df):
        """分析车手退赛"""
        if lap_data_df is None or len(lap_data_df) == 0:
            return

        print("\n分析退赛情况...")

        for car_idx in lap_data_df['car_index'].unique():
            car_data = lap_data_df[lap_data_df['car_index'] == car_idx].copy()
            car_data = car_data.sort_values('current_lap_num')

            # 检测退赛:result_status变为7或4 (7=retired, 4=dnf)
            retirements = car_data[
                (car_data['result_status'].isin([4, 7])) &
                (~car_data['result_status'].shift(1).isin([4, 7]))
            ]

            if len(retirements) > 0:
                retirement = retirements.iloc[0]
                self.retirements.append({
                    'car_index': car_idx,
                    'lap_num': float(retirement['current_lap_num']),
                    'timestamp': retirement['timestamp']
                })

        print(f"  找到 {len(self.retirements)} 次退赛")
        for ret in self.retirements:
            initials = self._get_driver_initials(ret['car_index'])
            print(f"    {initials}: 第{ret['lap_num']:.1f}圈")

    def analyze_strategies(self, lap_data_df, car_status_df):
        """分析车手策略(轮胎选择和进站圈数) - 使用visual_tyre_compound"""
        if lap_data_df is None or car_status_df is None:
            return

        print("\n分析比赛策略...")
        print("  使用 visual_tyre_compound 字段 (16=Soft/A3, 17=Medium/A4, 18=Hard/A6, 7=Inter/I, 8=Wet/W)")

        lap_data_df = lap_data_df.copy()
        car_status_df = car_status_df.copy()

        lap_data_df['timestamp'] = lap_data_df['timestamp'].astype(float).round(3)
        car_status_df['timestamp'] = car_status_df['timestamp'].astype(float).round(3)

        merged = pd.merge_asof(
            lap_data_df,
            car_status_df[['timestamp', 'car_index', 'visual_tyre_compound', 'tyres_age_laps']],
            on='timestamp',
            by='car_index',
            direction='nearest',
            tolerance=1
        )

        for car_idx in merged['car_index'].unique():
            car_data = merged[merged['car_index'] == car_idx].copy()
            car_data = car_data.sort_values('current_lap_num')
            car_data = car_data[car_data['visual_tyre_compound'].notna()]

            if len(car_data) == 0:
                continue

            # 检测轮胎更换
            car_data['tyre_change'] = (
                car_data['visual_tyre_compound'].ne(car_data['visual_tyre_compound'].shift()) |
                (car_data['tyres_age_laps'] < car_data['tyres_age_laps'].shift())
            )

            strategy = []
            for idx, row in car_data[car_data['tyre_change']].iterrows():
                compound_id = int(row['visual_tyre_compound'])
                compound = VISUAL_TYRE_COMPOUND_MAP.get(compound_id, f"Unknown_{compound_id}")

                lap_num = int(row['current_lap_num']) - 1 if row['current_lap_num'] > 0 else 0
                tyre_age = int(row['tyres_age_laps'])

                strategy.append([lap_num, compound, tyre_age, 0.0])

            if strategy:
                self.driver_strategies[car_idx] = strategy
                initials = self._get_driver_initials(car_idx)
                compounds_used = ' -> '.join([s[1] for s in strategy])
                print(f"    {initials}: {compounds_used}")

        print(f"  分析了 {len(self.driver_strategies)} 位车手的策略")

    def analyze_tyre_degradation(self, lap_data_df, car_status_df, telemetry_df):
        """分析轮胎降解数据 - 使用visual_tyre_compound"""
        if lap_data_df is None or car_status_df is None:
            return

        print("\n分析轮胎降解数据...")
        print("  使用 visual_tyre_compound 字段")

        lap_data_df = lap_data_df.copy()
        car_status_df = car_status_df.copy()

        lap_data_df['timestamp'] = lap_data_df['timestamp'].astype(float).round(3)
        car_status_df['timestamp'] = car_status_df['timestamp'].astype(float).round(3)
        lap_data_df['car_index'] = lap_data_df['car_index'].astype(int)
        car_status_df['car_index'] = car_status_df['car_index'].astype(int)

        merged = pd.merge_asof(
            lap_data_df,
            car_status_df[['timestamp', 'car_index', 'visual_tyre_compound', 'tyres_age_laps']],
            on='timestamp',
            by='car_index',
            direction='nearest',
            tolerance=1
        )

        print(f"  合并后数据: {len(merged)} 行")
        print(f"  包含轮胎数据的行: {merged['visual_tyre_compound'].notna().sum()}")

        for car_idx in merged['car_index'].unique():
            car_data = merged[merged['car_index'] == car_idx].copy()
            car_data = car_data.sort_values('current_lap_num')
            car_data = car_data[car_data['visual_tyre_compound'].notna()]

            if len(car_data) == 0:
                continue

            car_data['tyre_stint'] = (
                car_data['visual_tyre_compound'].ne(car_data['visual_tyre_compound'].shift()) |
                (car_data['tyres_age_laps'] < car_data['tyres_age_laps'].shift())
            ).cumsum()

            for stint_id in car_data['tyre_stint'].unique():
                stint_data = car_data[car_data['tyre_stint'] == stint_id]

                if len(stint_data) < 3:
                    continue

                compound = int(stint_data['visual_tyre_compound'].iloc[0])
                compound_name = VISUAL_TYRE_COMPOUND_MAP.get(compound, f"Unknown_{compound}")

                valid_data = stint_data[
                    (stint_data['last_lap_time_ms'] > 0) &
                    (stint_data['current_lap_invalid'] == 0)
                ]

                if len(valid_data) < 3:
                    continue

                for _, row in valid_data.iterrows():
                    self.tyre_degradation_data[car_idx][compound_name].append({
                        'tyre_age': int(row['tyres_age_laps']),
                        'lap_time_s': row['last_lap_time_ms'] / 1000.0,
                        'lap_num': int(row['current_lap_num'])
                    })

        total_stints = sum(len(compounds) for compounds in self.tyre_degradation_data.values())
        print(f"  找到 {total_stints} 个轮胎stint用于分析")
        for car_idx, compounds in self.tyre_degradation_data.items():
            if compounds:
                initials = self._get_driver_initials(car_idx)
                print(f"    {initials}: {', '.join(compounds.keys())}")

    def fit_tyre_degradation(self, tyre_data):
        """拟合轮胎降解曲线 - 线性模型"""
        if len(tyre_data) < 3:
            return None

        ages = np.array([d['tyre_age'] for d in tyre_data])
        lap_times = np.array([d['lap_time_s'] for d in tyre_data])

        # 移除异常值
        q1, q3 = np.percentile(lap_times, [25, 75])
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        mask = (lap_times >= lower_bound) & (lap_times <= upper_bound)

        ages = ages[mask]
        lap_times = lap_times[mask]

        if len(ages) < 3:
            return None

        try:
            slope, intercept, r_value, _, _ = stats.linregress(ages, lap_times)
            baseline = lap_times.min()
            k_0 = intercept - baseline
            k_1_lin = slope

            def quad_func(x, k0, k1, k2):
                return baseline + k0 + k1 * x + k2 * x**2

            try:
                popt_quad, _ = curve_fit(
                    quad_func, ages, lap_times,
                    p0=[k_0, k_1_lin, 0.0001],
                    maxfev=10000
                )
                k_0_quad, k_1_quad, k_2_quad = popt_quad
            except:
                k_0_quad, k_1_quad, k_2_quad = k_0, k_1_lin, 0.0001

            return {
                'k_0': round(max(0, k_0), 4),
                'k_1_lin': round(abs(k_1_lin), 4),
                'k_1_quad': round(abs(k_1_quad), 4),
                'k_2_quad': round(abs(k_2_quad), 6),
                'r_squared': round(r_value**2, 4),
                'n_samples': len(ages)
            }
        except Exception as e:
            print(f"    拟合失败: {e}")
            return None

    def calculate_track_parameters(self, lap_data_df, telemetry_df):
        """计算赛道参数"""
        if lap_data_df is None:
            return {}

        print("\n计算赛道参数...")

        valid_laps = lap_data_df[
            (lap_data_df['last_lap_time_ms'] > 0) &
            (lap_data_df['current_lap_invalid'] == 0)
        ]

        if len(valid_laps) == 0:
            return {}

        t_q = valid_laps['last_lap_time_ms'].min() / 1000.0
        fastest_laps = valid_laps.nsmallest(max(1, len(valid_laps) // 10), 'last_lap_time_ms')
        t_race = fastest_laps['last_lap_time_ms'].mean() / 1000.0
        t_gap_racepace = t_race - t_q

        # 计算进出站时间损失
        pit_stats = self._calculate_pit_drive_times()

        track_params = {
            't_q': round(t_q, 3),
            't_gap_racepace': round(max(0.5, t_gap_racepace), 3),
            't_lap_sens_mass': 0.03,
            't_pit_tirechange_min': 2.0,
            **pit_stats,  # 添加进出站时间
            'pits_aft_finishline': True,
            't_loss_pergridpos': round(t_q * 0.0015, 3),
            't_loss_firstlap': round(t_q * 0.025, 3),
            't_gap_overtake': 1.2,
            't_gap_overtake_vel': -0.035,
            't_drseffect': -0.5,
            'mult_t_lap_sc': 1.6,
            'mult_t_lap_fcy': 1.4
        }

        return track_params

    def _calculate_pit_drive_times(self):
        """计算进出站时间损失"""
        if not self.pit_stop_data:
            # 使用默认值
            return {
                't_pitdrive_inlap': 5.0,
                't_pitdrive_outlap': 15.0,
                't_pitdrive_inlap_fcy': 2.5,
                't_pitdrive_outlap_fcy': 12.0,
                't_pitdrive_inlap_sc': 0.5,
                't_pitdrive_outlap_sc': 11.0
            }

        # 计算平均进出站时间损失
        all_inlap = []
        all_outlap = []

        for stops in self.pit_stop_data.values():
            for stop in stops:
                all_inlap.append(stop['inlap_loss'])
                all_outlap.append(stop['outlap_loss'])

        avg_inlap = np.median(all_inlap) if all_inlap else 5.0
        avg_outlap = np.median(all_outlap) if all_outlap else 15.0

        return {
            't_pitdrive_inlap': round(avg_inlap, 3),
            't_pitdrive_outlap': round(avg_outlap, 3),
            't_pitdrive_inlap_fcy': round(avg_inlap * 0.5, 3),
            't_pitdrive_outlap_fcy': round(avg_outlap * 0.8, 3),
            't_pitdrive_inlap_sc': round(avg_inlap * 0.1, 3),
            't_pitdrive_outlap_sc': round(avg_outlap * 0.73, 3)
        }

    def _calculate_optimal_strategy(self, initials, total_laps, available_compounds, tireset_pars):
        """计算理论最优换胎策略(最小化总比赛时间)"""
        if initials not in tireset_pars or not available_compounds:
            # 返回默认2停策略
            return [[0, 'A4', 0, 0.0], [int(total_laps * 0.35), 'A3', 0, 0.0], [int(total_laps * 0.7), 'A4', 0, 0.0]]

        driver_tyre_pars = tireset_pars[initials]
        dry_compounds = [c for c in available_compounds if c.startswith('A')]

        if not dry_compounds:
            return [[0, 'A4', 0, 0.0]]

        # 获取每种轮胎的降解参数
        compound_params = {}
        for compound in dry_compounds:
            if compound in driver_tyre_pars:
                params = driver_tyre_pars[compound]
                compound_params[compound] = {
                    'k_0': params.get('k_0', 0.0),
                    'k_1_lin': params.get('k_1_lin', 0.08)
                }

        if not compound_params:
            return [[0, 'A4', 0, 0.0]]

        # 计算不同换胎策略的总时间
        # 假设进站损失:inlap + 换胎 + outlap ≈ 22-25秒
        PIT_STOP_TIME_LOSS = 23.0  # 秒

        # 尝试1停、2停、3停策略
        best_strategy = None
        best_time = float('inf')

        # 按降解率排序轮胎(从硬到软)
        sorted_compounds = sorted(compound_params.items(),
                                 key=lambda x: x[1]['k_1_lin'])

        for num_stops in range(1, 4):  # 1停、2停、3停
            # 尝试不同的进站时机和轮胎组合
            if num_stops == 1:
                # 1停策略:使用两种轮胎
                for start_compound in dry_compounds:
                    for second_compound in dry_compounds:
                        for pit_lap in range(int(total_laps * 0.3), int(total_laps * 0.7), 2):
                            total_time = self._calculate_strategy_time(
                                [[0, start_compound, 0, 0.0], [pit_lap, second_compound, 0, 0.0]],
                                total_laps, compound_params, PIT_STOP_TIME_LOSS
                            )
                            if total_time < best_time:
                                best_time = total_time
                                best_strategy = [[0, start_compound, 0, 0.0], [pit_lap, second_compound, 0, 0.0]]

            elif num_stops == 2:
                # 2停策略:使用三种轮胎
                for start_compound in dry_compounds:
                    for mid_compound in dry_compounds:
                        for end_compound in dry_compounds:
                            for pit1 in range(int(total_laps * 0.25), int(total_laps * 0.45), 3):
                                for pit2 in range(int(total_laps * 0.55), int(total_laps * 0.75), 3):
                                    if pit2 > pit1 + 5:  # 确保两次进站间隔
                                        total_time = self._calculate_strategy_time(
                                            [[0, start_compound, 0, 0.0],
                                             [pit1, mid_compound, 0, 0.0],
                                             [pit2, end_compound, 0, 0.0]],
                                            total_laps, compound_params, PIT_STOP_TIME_LOSS
                                        )
                                        if total_time < best_time:
                                            best_time = total_time
                                            best_strategy = [[0, start_compound, 0, 0.0],
                                                           [pit1, mid_compound, 0, 0.0],
                                                           [pit2, end_compound, 0, 0.0]]

            elif num_stops == 3:
                # 3停策略:使用多种轮胎
                if len(sorted_compounds) >= 3:
                    # 使用最硬、中等、最软的组合
                    hard = sorted_compounds[0][0]
                    medium = sorted_compounds[len(sorted_compounds)//2][0]
                    soft = sorted_compounds[-1][0]

                    pit1 = int(total_laps * 0.2)
                    pit2 = int(total_laps * 0.45)
                    pit3 = int(total_laps * 0.7)

                    strategy = [[0, medium, 0, 0.0],
                               [pit1, hard, 0, 0.0],
                               [pit2, soft, 0, 0.0],
                               [pit3, soft, 0, 0.0]]

                    total_time = self._calculate_strategy_time(
                        strategy, total_laps, compound_params, PIT_STOP_TIME_LOSS
                    )
                    if total_time < best_time:
                        best_time = total_time
                        best_strategy = strategy

        return best_strategy if best_strategy else [[0, 'A4', 0, 0.0]]

    def _calculate_strategy_time(self, strategy, total_laps, compound_params, pit_stop_loss):
        """计算策略的总时间(考虑轮胎降解和进站损失)"""
        total_time = 0.0
        pit_stops = len(strategy) - 1

        for i in range(len(strategy)):
            stint_start_lap = strategy[i][0]
            compound = strategy[i][1]

            # 计算stint结束圈
            if i < len(strategy) - 1:
                stint_end_lap = strategy[i + 1][0]
            else:
                stint_end_lap = total_laps

            stint_laps = stint_end_lap - stint_start_lap

            # 检查化合物参数是否存在
            if compound not in compound_params:
                # 使用平均值
                k_0 = 0.2
                k_1_lin = 0.08
            else:
                k_0 = compound_params[compound]['k_0']
                k_1_lin = compound_params[compound]['k_1_lin']

            # 计算这个stint的总时间(线性降解模型)
            # 每圈时间 = base_lap_time + k_0 + k_1_lin * tyre_age
            for lap in range(stint_laps):
                tyre_age = lap
                lap_time_delta = k_0 + k_1_lin * tyre_age
                total_time += lap_time_delta

        # 加上进站时间损失
        total_time += pit_stops * pit_stop_loss

        return total_time

    def generate_ini_content(self, csv_files):
        """生成完整的INI文件内容"""

        # 提取基本信息
        self.session_data = self.extract_session_info(csv_files['session'])
        self.participants = self.extract_participants_info(csv_files['participants'])

        # 分析数据
        self.analyze_lap_times(csv_files['lap_data'])
        self.analyze_pit_stops(csv_files['lap_data'])
        self.analyze_fcy_phases(csv_files['session'], csv_files['lap_data'])
        self.analyze_retirements(csv_files['lap_data'])
        self.analyze_strategies(csv_files['lap_data'], csv_files['car_status'])
        self.analyze_tyre_degradation(
            csv_files['lap_data'],
            csv_files['car_status'],
            csv_files['telemetry']
        )

        # 计算赛道参数
        track_params = self.calculate_track_parameters(
            csv_files['lap_data'],
            csv_files['telemetry']
        )

        # 生成INI内容
        ini_content = []
        ini_content.append("# encoding UTF-8")
        ini_content.append(f"# Generated from F1 25 telemetry data on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        ini_content.append("# Using visual_tyre_compound for strategy analysis")
        ini_content.append("")

        # [RACE_PARS]
        ini_content.append("[RACE_PARS]")
        participant_initials = [self._get_driver_initials(idx)
                               for idx in sorted(self.participants.keys())]

        race_pars = {
            'season': 2025,
            'tot_no_laps': self.session_data.get('total_laps', 50) if self.session_data else 50,
            'min_t_dist': 0.5,
            'min_t_dist_sc': 0.8,
            't_duel': 0.3,
            't_overtake_loser': 0.3,
            'use_drs': True,
            'drs_window': 1.0,
            'drs_allow_lap': 3,
            'drs_sc_delay': 2,
            'participants': participant_initials
        }

        ini_content.append(f'race_pars = {json.dumps(race_pars, indent=4, cls=NumpyEncoder, ensure_ascii=False)}')
        ini_content.append("")

        # [TRACK_PARS]
        ini_content.append("[TRACK_PARS]")
        track_name = self.session_data.get('track_name', 'Unknown') if self.session_data else 'Unknown'
        track_pars = {
            'name': track_name,
            **track_params
        }
        ini_content.append(f'track_pars = {json.dumps(track_pars, indent=4, cls=NumpyEncoder, ensure_ascii=False)}')
        ini_content.append("")

        # [CAR_PARS]
        ini_content.append("[CAR_PARS]")
        car_pars = self._generate_car_pars()
        ini_content.append(f'car_pars = {json.dumps(car_pars, indent=4, cls=NumpyEncoder, ensure_ascii=False)}')
        ini_content.append("")

        # [TIRESET_PARS] - 必须在VSE_PARS之前生成
        ini_content.append("[TIRESET_PARS]")
        tireset_pars = self._generate_tireset_pars()
        ini_content.append(f'tireset_pars = {json.dumps(tireset_pars, indent=4, cls=NumpyEncoder, ensure_ascii=False)}')
        ini_content.append("")

        # [DRIVER_PARS]
        ini_content.append("[DRIVER_PARS]")
        driver_pars = self._generate_driver_pars()
        ini_content.append(f'driver_pars = {json.dumps(driver_pars, indent=4, cls=NumpyEncoder, ensure_ascii=False)}')
        ini_content.append("")

        # [MONTE_CARLO_PARS]
        ini_content.append("[MONTE_CARLO_PARS]")
        monte_carlo_pars = self._generate_monte_carlo_pars()
        ini_content.append(f'monte_carlo_pars = {json.dumps(monte_carlo_pars, indent=4, cls=NumpyEncoder, ensure_ascii=False)}')
        ini_content.append("")

        # [EVENT_PARS]
        ini_content.append("[EVENT_PARS]")
        event_pars = self._generate_event_pars()
        ini_content.append(f'event_pars = {json.dumps(event_pars, indent=4, cls=NumpyEncoder, ensure_ascii=False)}')
        ini_content.append("")

        # [VSE_PARS] - 使用tireset_pars来计算最优策略
        ini_content.append("[VSE_PARS]")
        vse_pars = self._generate_vse_pars_with_optimization(tireset_pars)
        ini_content.append(f'vse_pars = {json.dumps(vse_pars, indent=4, cls=NumpyEncoder, ensure_ascii=False)}')
        ini_content.append("")

        return '\n'.join(ini_content)

    def _get_driver_initials(self, car_idx):
        """生成车手缩写"""
        if car_idx not in self.participants:
            return f"DR{car_idx}"

        name = self.participants[car_idx]['name']
        parts = name.upper().split()

        if len(parts) >= 2:
            return parts[-1][:3]
        else:
            return parts[0][:3] if parts else f"DR{car_idx}"

    def _generate_car_pars(self):
        """生成车辆参数"""
        teams = {}
        team_colors = {
            'Mercedes': '#00D2BE', 'Ferrari': '#DC0000', 'RedBull': '#1E41FF',
            'Williams': '#005AFF', 'AstonMartin': '#006F62', 'Alpine': '#0090FF',
            'RB': '#2B4562', 'Haas': '#B6BABD', 'McLaren': '#FF8700',
            'Sauber': '#00E701'
        }

        for car_idx, participant in self.participants.items():
            team = participant['team']
            if team not in teams:
                teams[team] = {
                    'drivetype': 'combustion',
                    'manufacturer': team,
                    't_car': 0.0,
                    'm_fuel': 110.0,
                    'b_fuel_perlap': 1.6,
                    'energy': None,
                    'energy_perlap': None,
                    'mult_consumption_sc': 0.25,
                    'mult_consumption_fcy': 0.5,
                    'auto_consumption_adjust': True,
                    't_pit_tirechange_add': round(np.random.uniform(0.4, 1.2), 3),
                    't_pit_refuel_perkg': None,
                    't_pit_charge_perkwh': None,
                    'color': team_colors.get(team, '#FFFFFF')
                }

        return teams

    def _generate_tireset_pars(self):
        """生成轮胎参数"""
        print("\n拟合轮胎降解参数...")
        tireset_pars = {}

        if not self.tyre_degradation_data:
            print("  ⚠ 警告: 没有找到轮胎降解数据,使用默认参数")
            for car_idx in self.participants.keys():
                initials = self._get_driver_initials(car_idx)
                tireset_pars[initials] = {
                    'tire_deg_model': 'lin',
                    'mult_tiredeg_sc': 0.25,
                    'mult_tiredeg_fcy': 0.5,
                    't_add_coldtires': 1.0,
                    'A3': {'k_0': 0.0, 'k_1_lin': 0.08, 'k_1_quad': 0.078, 'k_2_quad': 0.0001},
                    'A4': {'k_0': 0.2, 'k_1_lin': 0.10, 'k_1_quad': 0.095, 'k_2_quad': 0.0005},
                    'A6': {'k_0': 0.5, 'k_1_lin': 0.06, 'k_1_quad': 0.055, 'k_2_quad': 0.0003}
                }
            return tireset_pars

        for car_idx, compounds in self.tyre_degradation_data.items():
            initials = self._get_driver_initials(car_idx)
            tireset_pars[initials] = {
                'tire_deg_model': 'lin',
                'mult_tiredeg_sc': 0.25,
                'mult_tiredeg_fcy': 0.5,
                't_add_coldtires': 1.0
            }

            for compound, data in compounds.items():
                fit_result = self.fit_tyre_degradation(data)

                if fit_result:
                    tireset_pars[initials][compound] = {
                        'k_0': fit_result['k_0'],
                        'k_1_lin': fit_result['k_1_lin'],
                        'k_1_quad': fit_result['k_1_quad'],
                        'k_2_quad': fit_result['k_2_quad']
                    }
                    print(f"  ✓ {initials} - {compound}: "
                          f"k_1_lin={fit_result['k_1_lin']:.4f}, "
                          f"R²={fit_result['r_squared']:.3f}, "
                          f"n={fit_result['n_samples']}")

        return tireset_pars

    def _generate_driver_pars(self):
        """生成车手参数"""
        driver_pars = {}

        for car_idx, participant in self.participants.items():
            initials = self._get_driver_initials(car_idx)

            lap_times = self.driver_lap_times.get(car_idx, [])
            if lap_times:
                avg_lap_time = np.mean([lt['lap_time_s'] for lt in lap_times])
                fastest_lap = min([lt['lap_time_s'] for lt in lap_times])
                t_driver = avg_lap_time - fastest_lap
            else:
                t_driver = 0.0

            # 使用分析得到的策略或默认策略
            strategy = self.driver_strategies.get(car_idx, [[0, 'A4', 0, 0.0]])

            driver_pars[initials] = {
                'carno': participant['race_number'],
                'name': participant['name'],
                'initials': initials,
                'team': participant['team'],
                't_driver': round(max(0, t_driver), 3),
                'strategy_info': strategy,
                'p_grid': car_idx + 1,
                't_teamorder': 0.0,
                'vel_max': 330.0
            }

        return driver_pars

    def _generate_monte_carlo_pars(self):
        """生成蒙特卡洛参数"""
        # 找到最快的车手作为参考
        fastest_driver = None
        fastest_time = float('inf')

        for car_idx, lap_times in self.driver_lap_times.items():
            if lap_times:
                best_time = min([lt['lap_time_s'] for lt in lap_times])
                if best_time < fastest_time:
                    fastest_time = best_time
                    fastest_driver = car_idx

        ref_driver = self._get_driver_initials(fastest_driver) if fastest_driver else "HAM"

        return {
            'min_dist_sc': 1.5,
            'min_dist_vsc': 1.5,
            'ref_driver': ref_driver
        }

    def _generate_event_pars(self):
        """生成事件参数(FCY和退赛)"""
        # 转换FCY阶段为进度(圈数)
        fcy_phases = []
        for phase in self.fcy_phases:
            # 这里需要将时间戳转换为圈数进度
            # 简化处理:假设平均圈速
            fcy_phases.append([
                0.0,  # start progress (需要根据实际数据计算)
                0.0,  # end progress
                phase['type'],
                None,
                None
            ])

        # 转换退赛为进度 - 设置为[](允许模拟器随机生成)
        retirements = []  # 设置为[],让race simulation随机决定

        return {
            'fcy_data': {
                'phases': fcy_phases if fcy_phases else [],
                'domain': 'progress'
            },
            'retire_data': {
                'retirements': retirements,
                'domain': 'progress'
            }
        }

    def _generate_vse_pars_with_optimization(self, tireset_pars):
        """生成虚拟策略工程师参数(使用优化的base_strategy)"""
        # 收集所有使用过的轮胎配方
        all_compounds = set()
        for compounds in self.tyre_degradation_data.values():
            for compound in compounds.keys():
                all_compounds.add(compound)

        available = sorted(list(all_compounds)) if all_compounds else ["A3", "A4", "A6"]
        available.extend(["I", "W"])  # 添加雨胎
        dry_compounds = [c for c in available if c.startswith('A')]

        # 获取总圈数
        total_laps = self.session_data.get('total_laps', 50) if self.session_data else 50

        # 生成基础策略和实际策略
        base_strategy = {}
        real_strategy = {}

        print("\n计算理论最优策略...")

        for car_idx in self.participants.keys():
            initials = self._get_driver_initials(car_idx)

            # 实际策略:使用分析得到的策略
            if car_idx in self.driver_strategies:
                real_strategy[initials] = self.driver_strategies[car_idx]
            else:
                # 默认策略
                default_strat = [[0, 'A4', 0, 0.0], [int(total_laps * 0.5), 'A3', 0, 0.0]]
                real_strategy[initials] = default_strat

            # 基础策略:计算理论最优策略
            optimal_strategy = self._calculate_optimal_strategy(
                initials, total_laps, dry_compounds, tireset_pars
            )
            base_strategy[initials] = optimal_strategy

            # 打印对比
            print(f"  {initials}:")
            print(f"    理论最优: {len(optimal_strategy)-1}停 - {' -> '.join([s[1] for s in optimal_strategy])}")
            if initials in real_strategy:
                print(f"    实际策略: {len(real_strategy[initials])-1}停 - {' -> '.join([s[1] for s in real_strategy[initials]])}")

        # VSE类型(全部使用supervised)
        vse_type = {initials: 'supervised' for initials in base_strategy.keys()}

        return {
            'available_compounds': available,
            'param_dry_compounds': dry_compounds,
            'location_cat': 2,
            'base_strategy': base_strategy,
            'real_strategy': real_strategy,
            'vse_type': vse_type
        }

    def convert(self, output_filename=None):
        """执行转换"""
        print("=" * 70)
        print("F1 25 遥测数据转换为INI格式(增强版)")
        print("使用 visual_tyre_compound 进行轮胎分析")
        print("=" * 70)

        csv_files = self.load_csv_files()

        if not any(df is not None for df in csv_files.values()):
            print("\n错误: 未找到有效的CSV文件!")
            return

        ini_content = self.generate_ini_content(csv_files)

        if output_filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"race_pars_{timestamp}.ini"

        with open(output_filename, 'w', encoding='utf-8') as f:
            f.write(ini_content)

        print(f"\n{'=' * 70}")
        print(f"✓ 转换完成! 输出文件: {output_filename}")
        print(f"{'=' * 70}")
        print(f"\n已包含的参数:")
        print(f"  ✓ RACE_PARS (比赛基本参数)")
        print(f"  ✓ TRACK_PARS (赛道参数,包含进出站时间)")
        print(f"  ✓ CAR_PARS (车辆参数)")
        print(f"  ✓ TIRESET_PARS (轮胎降解参数)")
        print(f"  ✓ DRIVER_PARS (车手参数和策略)")
        print(f"  ✓ MONTE_CARLO_PARS (蒙特卡洛参数)")
        print(f"  ✓ EVENT_PARS (FCY阶段和退赛)")
        print(f"  ✓ VSE_PARS (虚拟策略工程师)")
        print(f"\n新增功能:")
        print(f"  ✓ base_strategy: 基于轮胎降解模型的理论最优策略")
        print(f"  ✓ real_strategy: 从遥测数据分析的实际比赛策略")
        print(f"  ✓ 使用 visual_tyre_compound (16=A3, 17=A4, 18=A6, 7=I, 8=W)")

if __name__ == "__main__":
    # 创建转换器实例
    converter = F1DataConverter(data_dir="f1_telemetry_data_Shanghai")

    # 执行转换
    converter.convert()