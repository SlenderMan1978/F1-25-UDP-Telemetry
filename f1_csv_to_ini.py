"""
F1 25 CSV Telemetry Data to INI Converter
将F1 25游戏收集的CSV遥测数据转换为race simulation所需的.ini格式
"""

import pandas as pd
import numpy as np
from scipy.optimize import curve_fit
from scipy import stats
import os
import json
from collections import defaultdict
from datetime import datetime

# 自定义JSON编码器，处理numpy/pandas类型
class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64, np.float32)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)

# 轮胎化合物映射 (根据F1 25 UDP规范)
TYRE_COMPOUND_MAP = {
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

# Driver ID映射表 (来自F1 25 UDP规范)
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

            # 跳过无效的车辆索引 - driver_id或team_id为255的都忽略
            if team_id == 255 or driver_id == 255:
                continue

            # 使用driver_id映射获取driver姓名
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

            # 提取有效圈速 (last_lap_time_ms > 0 且 current_lap_invalid == 0)
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

    def analyze_tyre_degradation(self, lap_data_df, car_status_df, telemetry_df):
        """分析轮胎降解数据"""
        if lap_data_df is None or car_status_df is None:
            return

        print("\n分析轮胎降解数据...")

        # 确保timestamp和car_index类型一致
        lap_data_df = lap_data_df.copy()
        car_status_df = car_status_df.copy()

        lap_data_df['timestamp'] = lap_data_df['timestamp'].astype(float).round(3)
        car_status_df['timestamp'] = car_status_df['timestamp'].astype(float).round(3)
        lap_data_df['car_index'] = lap_data_df['car_index'].astype(int)
        car_status_df['car_index'] = car_status_df['car_index'].astype(int)

        # 合并数据 - 使用nearest时间匹配
        merged = pd.merge_asof(
            lap_data_df,
            car_status_df[['timestamp', 'car_index', 'actual_tyre_compound', 'tyres_age_laps']],
            on='timestamp',
            by='car_index',
            direction='nearest',
            tolerance=1
        )

        print(f"  合并后数据: {len(merged)} 行")
        print(f"  包含轮胎数据的行: {merged['actual_tyre_compound'].notna().sum()}")

        for car_idx in merged['car_index'].unique():
            car_data = merged[merged['car_index'] == car_idx].copy()
            car_data = car_data.sort_values('current_lap_num')

            # 只保留有轮胎数据的行
            car_data = car_data[car_data['actual_tyre_compound'].notna()]

            if len(car_data) == 0:
                continue

            # 按轮胎stint分组
            car_data['tyre_stint'] = (
                car_data['actual_tyre_compound'].ne(car_data['actual_tyre_compound'].shift()) |
                (car_data['tyres_age_laps'] < car_data['tyres_age_laps'].shift())
            ).cumsum()

            for stint_id in car_data['tyre_stint'].unique():
                stint_data = car_data[car_data['tyre_stint'] == stint_id]

                if len(stint_data) < 3:  # 至少需要3个数据点
                    continue

                compound = int(stint_data['actual_tyre_compound'].iloc[0])
                compound_name = TYRE_COMPOUND_MAP.get(compound, f"Unknown_{compound}")

                # 提取圈速和轮胎年龄
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

        # 打印统计信息
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

        # 提取数据
        ages = np.array([d['tyre_age'] for d in tyre_data])
        lap_times = np.array([d['lap_time_s'] for d in tyre_data])

        # 移除异常值 (使用IQR方法)
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
            # 线性拟合: lap_time = k_0 + k_1_lin * age
            slope, intercept, r_value, _, _ = stats.linregress(ages, lap_times)

            # 计算基准圈速 (新轮胎)
            baseline = lap_times.min()
            k_0 = intercept - baseline
            k_1_lin = slope

            # 二次拟合: lap_time = k_0 + k_1_quad * age + k_2_quad * age^2
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

        # 找到最快圈速 (qualifying lap time)
        valid_laps = lap_data_df[
            (lap_data_df['last_lap_time_ms'] > 0) &
            (lap_data_df['current_lap_invalid'] == 0)
        ]

        if len(valid_laps) == 0:
            return {}

        t_q = valid_laps['last_lap_time_ms'].min() / 1000.0

        # 计算比赛配速差距 (取前10%最快圈速的平均值作为race pace)
        fastest_laps = valid_laps.nsmallest(max(1, len(valid_laps) // 10), 'last_lap_time_ms')
        t_race = fastest_laps['last_lap_time_ms'].mean() / 1000.0
        t_gap_racepace = t_race - t_q

        # 估算其他参数 (基于典型F1赛道)
        track_params = {
            't_q': round(t_q, 3),
            't_gap_racepace': round(max(0.5, t_gap_racepace), 3),
            't_lap_sens_mass': 0.03,  # 典型值: ~30ms/kg
            't_pit_tirechange_min': 2.0,
            't_loss_pergridpos': round(t_q * 0.0015, 3),  # ~0.15% per position
            't_loss_firstlap': round(t_q * 0.025, 3),  # ~2.5%
            't_gap_overtake': 1.2,
            't_gap_overtake_vel': -0.035,
            't_drseffect': -0.5,
            'mult_t_lap_sc': 1.6,
            'mult_t_lap_fcy': 1.4
        }

        return track_params

    def generate_ini_content(self, csv_files):
        """生成完整的INI文件内容"""

        # 提取基本信息
        session_info = self.extract_session_info(csv_files['session'])
        self.participants = self.extract_participants_info(csv_files['participants'])

        # 分析数据
        self.analyze_lap_times(csv_files['lap_data'])
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
        ini_content.append("")

        # [RACE_PARS]
        ini_content.append("[RACE_PARS]")
        participant_initials = [self._get_driver_initials(idx)
                               for idx in sorted(self.participants.keys())]

        race_pars = {
            'season': 2025,
            'tot_no_laps': session_info.get('total_laps', 50) if session_info else 50,
            'min_t_dist': 0.5,
            'min_t_dist_sc': 0.8,
            't_duel': 0.3,
            't_overtake_loser': 0.3,
            'use_drs': 'true',
            'drs_window': 1.0,
            'drs_allow_lap': 3,
            'drs_sc_delay': 2,
            'participants': participant_initials  # 直接使用列表，不转换为字符串
        }

        ini_content.append(f'race_pars = {json.dumps(race_pars, indent=4, cls=NumpyEncoder, ensure_ascii=False)}')
        ini_content.append("")

        # [TRACK_PARS]
        ini_content.append("[TRACK_PARS]")
        track_name = session_info.get('track_name', 'Unknown') if session_info else 'Unknown'
        track_pars = {
            'name': track_name,
            **track_params,
            'pits_aft_finishline': True
        }
        ini_content.append(f'track_pars = {json.dumps(track_pars, indent=4, cls=NumpyEncoder, ensure_ascii=False)}')
        ini_content.append("")

        # [CAR_PARS]
        ini_content.append("[CAR_PARS]")
        car_pars = self._generate_car_pars()
        ini_content.append(f'car_pars = {json.dumps(car_pars, indent=4, cls=NumpyEncoder, ensure_ascii=False)}')
        ini_content.append("")

        # [TIRESET_PARS]
        ini_content.append("[TIRESET_PARS]")
        tireset_pars = self._generate_tireset_pars()
        ini_content.append(f'tireset_pars = {json.dumps(tireset_pars, indent=4, cls=NumpyEncoder, ensure_ascii=False)}')
        ini_content.append("")

        # [DRIVER_PARS]
        ini_content.append("[DRIVER_PARS]")
        driver_pars = self._generate_driver_pars()
        ini_content.append(f'driver_pars = {json.dumps(driver_pars, indent=4, cls=NumpyEncoder, ensure_ascii=False)}')
        ini_content.append("")

        return '\n'.join(ini_content)

    def _get_driver_initials(self, car_idx):
        """生成车手缩写 - 使用姓氏的前三位字母"""
        if car_idx not in self.participants:
            return f"DR{car_idx}"

        name = self.participants[car_idx]['name']
        parts = name.upper().split()

        if len(parts) >= 2:
            # 使用姓氏（最后一个单词）的前3个字母
            return parts[-1][:3]
        else:
            # 如果只有一个单词，使用前3个字母
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
        """生成轮胎参数 (含拟合结果)"""
        print("\n拟合轮胎降解参数...")
        tireset_pars = {}

        if not self.tyre_degradation_data:
            print("  ⚠ 警告: 没有找到轮胎降解数据，使用默认参数")
            # 为所有参赛者生成默认参数
            for car_idx in self.participants.keys():
                initials = self._get_driver_initials(car_idx)
                tireset_pars[initials] = {
                    'tire_deg_model': 'lin',
                    'mult_tiredeg_sc': 0.25,
                    'mult_tiredeg_fcy': 0.5,
                    't_add_coldtires': 1.0,
                    'A3': {'k_0': 0.0, 'k_1_lin': 0.08, 'k_1_quad': 0.078, 'k_2_quad': 0.0001},
                    'A4': {'k_0': 0.2, 'k_1_lin': 0.10, 'k_1_quad': 0.095, 'k_2_quad': 0.0005},
                    'A5': {'k_0': 0.5, 'k_1_lin': 0.06, 'k_1_quad': 0.055, 'k_2_quad': 0.0003}
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
                if compound.startswith('C') or compound in ['I', 'W']:
                    fit_result = self.fit_tyre_degradation(data)

                    if fit_result:
                        # 使用简化的化合物名称 (A3=C3, A4=C4等)
                        if compound.startswith('C'):
                            compound_key = f"A{compound[1]}"
                        else:
                            compound_key = compound

                        tireset_pars[initials][compound_key] = {
                            'k_0': fit_result['k_0'],
                            'k_1_lin': fit_result['k_1_lin'],
                            'k_1_quad': fit_result['k_1_quad'],
                            'k_2_quad': fit_result['k_2_quad']
                        }
                        print(f"  ✓ {initials} - {compound_key}: "
                              f"k_1_lin={fit_result['k_1_lin']:.4f}, "
                              f"R²={fit_result['r_squared']:.3f}, "
                              f"n={fit_result['n_samples']}")

        return tireset_pars

    def _generate_driver_pars(self):
        """生成车手参数"""
        driver_pars = {}

        for car_idx, participant in self.participants.items():
            initials = self._get_driver_initials(car_idx)

            # 计算平均圈速作为车手能力指标
            lap_times = self.driver_lap_times.get(car_idx, [])
            if lap_times:
                avg_lap_time = np.mean([lt['lap_time_s'] for lt in lap_times])
                fastest_lap = min([lt['lap_time_s'] for lt in lap_times])
                t_driver = avg_lap_time - fastest_lap
            else:
                t_driver = 0.0

            driver_pars[initials] = {
                'carno': participant['race_number'],
                'name': participant['name'],
                'initials': initials,
                'team': participant['team'],
                't_driver': round(max(0, t_driver), 3),
                'strategy_info': [[0, 'A4', 0, 0.0]],  # 默认策略
                'p_grid': car_idx + 1,
                't_teamorder': 0.0,
                'vel_max': 330.0
            }

        return driver_pars

    def convert(self, output_filename=None):
        """执行转换"""
        print("=" * 70)
        print("F1 25 遥测数据转换为INI格式")
        print("=" * 70)

        # 加载CSV文件
        csv_files = self.load_csv_files()

        if not any(df is not None for df in csv_files.values()):
            print("\n错误: 未找到有效的CSV文件!")
            return

        # 生成INI内容
        ini_content = self.generate_ini_content(csv_files)

        # 保存文件
        if output_filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"race_pars_{timestamp}.ini"

        with open(output_filename, 'w', encoding='utf-8') as f:
            f.write(ini_content)

        print(f"\n{'=' * 70}")
        print(f"✓ 转换完成! 输出文件: {output_filename}")
        print(f"{'=' * 70}")


if __name__ == "__main__":
    # 创建转换器实例
    converter = F1DataConverter(data_dir="f1_telemetry_data")

    # 执行转换
    converter.convert()