"""
F1 25 Telemetry Data Collector
收集F1 25游戏的UDP遥测数据并保存到CSV文件用于AI训练
"""

import socket
import struct
import csv
import os
from datetime import datetime
from collections import defaultdict
import threading
import time

# 常量定义
MAX_CARS = 22
UDP_PORT = 20777  # F1游戏默认UDP端口,可在游戏设置中修改
COLLECTION_INTERVAL = 1.0  # 数据收集间隔(秒)


# 数据包ID枚举
class PacketID:
    MOTION = 0
    SESSION = 1
    LAP_DATA = 2
    EVENT = 3
    PARTICIPANTS = 4
    CAR_SETUPS = 5
    CAR_TELEMETRY = 6
    CAR_STATUS = 7
    FINAL_CLASSIFICATION = 8
    LOBBY_INFO = 9
    CAR_DAMAGE = 10
    SESSION_HISTORY = 11
    TYRE_SETS = 12
    MOTION_EX = 13
    TIME_TRIAL = 14
    LAP_POSITIONS = 15


class F1TelemetryCollector:
    def __init__(self, output_dir="f1_telemetry_data", port=UDP_PORT):
        self.port = port
        self.output_dir = output_dir
        self.running = False
        self.session_uid = None
        self.csv_writers = {}
        self.csv_files = {}
        self.last_collection_time = {}  # 记录每种数据类型的上次收集时间

        # 创建输出目录
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # 初始化CSV文件
        self._init_csv_files()

    def _init_csv_files(self):
        """初始化所有CSV文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Motion数据
        self._create_csv('motion', timestamp, [
            'timestamp', 'session_uid', 'frame', 'car_index',
            'world_pos_x', 'world_pos_y', 'world_pos_z',
            'world_vel_x', 'world_vel_y', 'world_vel_z',
            'g_force_lateral', 'g_force_longitudinal', 'g_force_vertical',
            'yaw', 'pitch', 'roll'
        ])

        # Telemetry数据
        self._create_csv('telemetry', timestamp, [
            'timestamp', 'session_uid', 'frame', 'car_index',
            'speed', 'throttle', 'steer', 'brake', 'clutch', 'gear',
            'engine_rpm', 'drs', 'rev_lights_percent',
            'brake_temp_rl', 'brake_temp_rr', 'brake_temp_fl', 'brake_temp_fr',
            'tyre_surface_temp_rl', 'tyre_surface_temp_rr', 'tyre_surface_temp_fl', 'tyre_surface_temp_fr',
            'tyre_inner_temp_rl', 'tyre_inner_temp_rr', 'tyre_inner_temp_fl', 'tyre_inner_temp_fr',
            'engine_temp', 'tyre_pressure_rl', 'tyre_pressure_rr', 'tyre_pressure_fl', 'tyre_pressure_fr'
        ])

        # Lap数据
        self._create_csv('lap_data', timestamp, [
            'timestamp', 'session_uid', 'frame', 'car_index',
            'last_lap_time_ms', 'current_lap_time_ms', 'sector1_time_ms',
            'sector2_time_ms', 'lap_distance', 'total_distance',
            'car_position', 'current_lap_num', 'pit_status', 'num_pit_stops',
            'sector', 'current_lap_invalid', 'penalties', 'grid_position',
            'driver_status', 'result_status'
        ])

        # Car Status数据
        self._create_csv('car_status', timestamp, [
            'timestamp', 'session_uid', 'frame', 'car_index',
            'traction_control', 'anti_lock_brakes', 'fuel_mix', 'front_brake_bias',
            'pit_limiter_status', 'fuel_in_tank', 'fuel_capacity', 'fuel_remaining_laps',
            'max_rpm', 'idle_rpm', 'max_gears', 'drs_allowed', 'drs_activation_distance',
            'actual_tyre_compound', 'visual_tyre_compound', 'tyres_age_laps',
            'vehicle_fia_flags', 'engine_power_ice', 'engine_power_mguk',
            'ers_store_energy', 'ers_deploy_mode', 'ers_harvested_mguk',
            'ers_harvested_mguh', 'ers_deployed_this_lap'
        ])

        # Car Damage数据
        self._create_csv('car_damage', timestamp, [
            'timestamp', 'session_uid', 'frame', 'car_index',
            'tyre_wear_rl', 'tyre_wear_rr', 'tyre_wear_fl', 'tyre_wear_fr',
            'tyre_damage_rl', 'tyre_damage_rr', 'tyre_damage_fl', 'tyre_damage_fr',
            'brake_damage_rl', 'brake_damage_rr', 'brake_damage_fl', 'brake_damage_fr',
            'front_left_wing_damage', 'front_right_wing_damage', 'rear_wing_damage',
            'floor_damage', 'diffuser_damage', 'sidepod_damage',
            'drs_fault', 'ers_fault', 'gearbox_damage', 'engine_damage',
            'engine_mguh_wear', 'engine_es_wear', 'engine_ce_wear',
            'engine_ice_wear', 'engine_mguk_wear', 'engine_tc_wear',
            'engine_blown', 'engine_seized'
        ])

        # Session数据
        self._create_csv('session', timestamp, [
            'timestamp', 'session_uid', 'frame',
            'weather', 'track_temperature', 'air_temperature', 'total_laps',
            'track_length', 'session_type', 'track_id', 'formula',
            'session_time_left', 'session_duration', 'pit_speed_limit',
            'safety_car_status', 'network_game'
        ])

        # Car Setups数据
        self._create_csv('car_setups', timestamp, [
            'timestamp', 'session_uid', 'frame', 'car_index',
            'front_wing', 'rear_wing', 'on_throttle_diff', 'off_throttle_diff',
            'front_camber', 'rear_camber', 'front_toe', 'rear_toe',
            'front_suspension', 'rear_suspension', 'front_anti_roll_bar', 'rear_anti_roll_bar',
            'front_suspension_height', 'rear_suspension_height',
            'brake_pressure', 'brake_bias', 'engine_braking',
            'tyre_pressure_rl', 'tyre_pressure_rr', 'tyre_pressure_fl', 'tyre_pressure_fr',
            'ballast', 'fuel_load'
        ])

        # Motion Ex数据(仅玩家车辆)
        self._create_csv('motion_ex', timestamp, [
            'timestamp', 'session_uid', 'frame',
            'suspension_pos_rl', 'suspension_pos_rr', 'suspension_pos_fl', 'suspension_pos_fr',
            'suspension_vel_rl', 'suspension_vel_rr', 'suspension_vel_fl', 'suspension_vel_fr',
            'suspension_acc_rl', 'suspension_acc_rr', 'suspension_acc_fl', 'suspension_acc_fr',
            'wheel_speed_rl', 'wheel_speed_rr', 'wheel_speed_fl', 'wheel_speed_fr',
            'wheel_slip_ratio_rl', 'wheel_slip_ratio_rr', 'wheel_slip_ratio_fl', 'wheel_slip_ratio_fr',
            'wheel_slip_angle_rl', 'wheel_slip_angle_rr', 'wheel_slip_angle_fl', 'wheel_slip_angle_fr',
            'wheel_lat_force_rl', 'wheel_lat_force_rr', 'wheel_lat_force_fl', 'wheel_lat_force_fr',
            'wheel_long_force_rl', 'wheel_long_force_rr', 'wheel_long_force_fl', 'wheel_long_force_fr',
            'height_of_cog', 'local_velocity_x', 'local_velocity_y', 'local_velocity_z',
            'angular_velocity_x', 'angular_velocity_y', 'angular_velocity_z',
            'angular_acceleration_x', 'angular_acceleration_y', 'angular_acceleration_z',
            'front_wheels_angle', 'wheel_vert_force_rl', 'wheel_vert_force_rr',
            'wheel_vert_force_fl', 'wheel_vert_force_fr'
        ])

        self._create_csv('final_classification',timestamp,[
            'timestamp', 'session_uid', 'frame','car_index',
            'position', 'num_laps', 'grid_position', 'points', 'num_pit_stops',
            'result_status', 'result_reason',
            'best_lap_time_ms', 'total_race_time',
            'penalties_time', 'num_penalties', 'num_tyre_stints',
        ])

        self._create_csv('participants',timestamp,[
            'timestamp', 'session_uid', 'frame','car_index',
            'ai_controlled', 'driver_id', 'network_id', 'team_id', 'my_team',
            'race_number', 'nationality', 'name', 'your_telemetry', 'show_online_names',
            'tech_level', 'platform'
        ])

        # 初始化所有数据类型的上次收集时间
        for key in self.csv_writers.keys():
            self.last_collection_time[key] = 0

    def _create_csv(self, name, timestamp, headers):
        """创建CSV文件并初始化writer"""
        filename = os.path.join(self.output_dir, f"{name}_{timestamp}.csv")
        file = open(filename, 'w', newline='', encoding='utf-8')
        writer = csv.writer(file)
        writer.writerow(headers)
        self.csv_files[name] = file
        self.csv_writers[name] = writer
        print(f"创建CSV文件: {filename}")

    def _should_collect(self, data_type):
        """检查是否应该收集该类型的数据(基于时间间隔)"""
        current_time = time.time()
        if current_time - self.last_collection_time.get(data_type, 0) >= COLLECTION_INTERVAL:
            self.last_collection_time[data_type] = current_time
            return True
        return False

    def _parse_header(self, data):
        """解析数据包头部"""
        try:
            header_format = '<HBBBBBQfIIBB'
            header_size = struct.calcsize(header_format)
            if len(data) < header_size:
                return None, 0

            header = struct.unpack(header_format, data[:header_size])
            return {
                'packet_format': header[0],
                'game_year': header[1],
                'game_major_version': header[2],
                'game_minor_version': header[3],
                'packet_version': header[4],
                'packet_id': header[5],
                'session_uid': header[6],
                'session_time': header[7],
                'frame_identifier': header[8],
                'overall_frame_identifier': header[9],
                'player_car_index': header[10],
                'secondary_player_car_index': header[11]
            }, header_size
        except struct.error as e:
            print(f"解析头部错误: {e}")
            return None, 0

    def _parse_motion_packet(self, data, header):
        """解析Motion数据包"""
        if not self._should_collect('motion'):
            return

        offset = 29  # 头部大小
        timestamp = time.time()

        try:
            for car_idx in range(MAX_CARS):
                car_format = '<ffffffhhhhhhffffff'
                car_size = struct.calcsize(car_format)
                if offset + car_size > len(data):
                    break

                car_data = struct.unpack(car_format, data[offset:offset + car_size])

                row = [
                    timestamp, header['session_uid'], header['frame_identifier'], car_idx,
                    car_data[0], car_data[1], car_data[2],  # world position
                    car_data[3], car_data[4], car_data[5],  # world velocity
                    car_data[12], car_data[13], car_data[14],  # g-forces
                    car_data[15], car_data[16], car_data[17]  # yaw, pitch, roll
                ]
                self.csv_writers['motion'].writerow(row)
                offset += car_size
        except (struct.error, IndexError) as e:
            print(f"解析Motion数据错误: {e}")

    def _parse_telemetry_packet(self, data, header):
        """解析Telemetry数据包"""
        if not self._should_collect('telemetry'):
            return

        offset = 29
        timestamp = time.time()

        try:
            for car_idx in range(MAX_CARS):
                car_format = '<HfffBbHBBHHHHHBBBBBBBBHffffBBBB'
                car_size = struct.calcsize(car_format)
                if offset + car_size > len(data):
                    break

                car_data = struct.unpack(car_format, data[offset:offset + car_size])

                row = [
                    timestamp, header['session_uid'], header['frame_identifier'], car_idx,
                    car_data[0],  # speed
                    car_data[1], car_data[2], car_data[3],  # throttle, steer, brake
                    car_data[4], car_data[5], car_data[6],  # clutch, gear, rpm
                    car_data[7], car_data[8],  # drs, rev_lights
                    car_data[9], car_data[10], car_data[11], car_data[12],  # brake temps
                    car_data[13], car_data[14], car_data[15], car_data[16],  # tyre surface temps
                    car_data[17], car_data[18], car_data[19], car_data[20],  # tyre inner temps
                    car_data[21],  # engine temp
                    car_data[22], car_data[23], car_data[24], car_data[25]  # tyre pressures
                ]
                self.csv_writers['telemetry'].writerow(row)
                offset += car_size
        except (struct.error, IndexError) as e:
            print(f"解析Telemetry数据错误: {e}")

    def _parse_lap_data_packet(self, data, header):
        """解析Lap Data数据包"""
        if not self._should_collect('lap_data'):
            return

        offset = 29
        timestamp = time.time()

        try:
            for car_idx in range(MAX_CARS):
                car_format = '<IIHBHBHBHBfffBBBBBBBBBBBBBBBHHBfB'
                car_size = struct.calcsize(car_format)
                if offset + car_size > len(data):
                    break

                car_data = struct.unpack(car_format, data[offset:offset + car_size])

                row = [
                    timestamp, header['session_uid'], header['frame_identifier'], car_idx,
                    car_data[0], car_data[1],  # last lap time, current lap time
                    car_data[2], car_data[4],  # sector times (simplified)
                    car_data[10], car_data[11],  # lap distance, total distance
                    car_data[13], car_data[14], car_data[15], car_data[16],
                    # position, lap num, pit status, num pit stops
                    car_data[17], car_data[18], car_data[19], car_data[24],  # sector, invalid, penalties, grid position
                    car_data[25], car_data[26]  # driver status, result status
                ]
                self.csv_writers['lap_data'].writerow(row)
                offset += car_size
        except (struct.error, IndexError) as e:
            print(f"解析Lap Data数据错误: {e}")

    def _parse_car_status_packet(self, data, header):
        """解析Car Status数据包"""
        if not self._should_collect('car_status'):
            return

        offset = 29
        timestamp = time.time()

        try:
            for car_idx in range(MAX_CARS):
                car_format = '<BBBBBfffHHBBHBBBbfffBfffB'
                car_size = struct.calcsize(car_format)
                if offset + car_size > len(data):
                    break

                car_data = struct.unpack(car_format, data[offset:offset + car_size])

                row = [
                    timestamp, header['session_uid'], header['frame_identifier'], car_idx,
                    car_data[0], car_data[1], car_data[2], car_data[3],  # TC, ABS, fuel mix, brake bias
                    car_data[4], car_data[5], car_data[6], car_data[7],  # pit limiter, fuel
                    car_data[8], car_data[9], car_data[10], car_data[11], car_data[12],  # RPM, gears, DRS
                    car_data[13], car_data[14], car_data[15], car_data[16],  # tyres
                    car_data[17], car_data[18], car_data[19],  # flags, engine power
                    car_data[20], car_data[21], car_data[22], car_data[23], car_data[24]  # ERS
                ]
                self.csv_writers['car_status'].writerow(row)
                offset += car_size
        except (struct.error, IndexError) as e:
            print(f"解析Car Status数据错误: {e}")

    def _parse_car_damage_packet(self, data, header):
        """解析Car Damage数据包"""
        if not self._should_collect('car_damage'):
            return

        offset = 29
        timestamp = time.time()
        try:
            for car_idx in range(MAX_CARS):
                car_format = '<ffffBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB'
                car_size = struct.calcsize(car_format)
                if offset + car_size > len(data):
                    break

                car_data = struct.unpack(car_format, data[offset:offset + car_size])
                row = [timestamp, header['session_uid'], header['frame_identifier'], car_idx] + list(car_data)
                self.csv_writers['car_damage'].writerow(row)
                offset += car_size
        except (struct.error, IndexError) as e:
            print(f"解析Car Damage数据错误: {e}")

    def _parse_session_packet(self, data, header):
        """解析Session数据包"""
        if not self._should_collect('session'):
            return

        timestamp = time.time()

        try:
            session_format = '<BbbBHBbBHHBBBBBB'
            session_size = struct.calcsize(session_format)
            if 29 + session_size > len(data):
                return

            session_data = struct.unpack(session_format, data[29:29 + session_size])

            row = [
                timestamp, header['session_uid'], header['frame_identifier'],
                session_data[0], session_data[1], session_data[2],  # weather, temps
                session_data[3], session_data[4], session_data[5], session_data[6], session_data[7],  # laps, track info
                session_data[8], session_data[9], session_data[10],  # session times, pit speed
                session_data[13], session_data[14]  # safety car, network game
            ]
            self.csv_writers['session'].writerow(row)
        except (struct.error, IndexError) as e:
            print(f"解析Session数据错误: {e}")

    def _parse_car_setups_packet(self, data, header):
        """解析Car Setups数据包"""
        if not self._should_collect('car_setups'):
            return

        offset = 29
        timestamp = time.time()

        try:
            for car_idx in range(MAX_CARS):
                car_format = '<BBBBffffBBBBBBBBBffffBf'
                car_size = struct.calcsize(car_format)
                if offset + car_size > len(data):
                    break

                car_data = struct.unpack(car_format, data[offset:offset + car_size])

                row = [timestamp, header['session_uid'], header['frame_identifier'], car_idx] + list(car_data)
                self.csv_writers['car_setups'].writerow(row)
                offset += car_size
        except (struct.error, IndexError) as e:
            print(f"解析Car Setups数据错误: {e}")

    def _parse_motion_ex_packet(self, data, header):
        """解析Motion Ex数据包(仅玩家车辆)"""
        if not self._should_collect('motion_ex'):
            return

        timestamp = time.time()
        offset = 29

        try:
            # 解析所有浮点数数据
            motion_ex_format = '<' + 'f' * 61  # 61个浮点数
            motion_ex_size = struct.calcsize(motion_ex_format)
            if offset + motion_ex_size > len(data):
                return

            motion_ex_data = struct.unpack(motion_ex_format, data[offset:offset + motion_ex_size])

            row = [timestamp, header['session_uid'], header['frame_identifier']] + list(motion_ex_data[:47])
            self.csv_writers['motion_ex'].writerow(row)
        except (struct.error, IndexError) as e:
            print(f"解析Motion Ex数据错误: {e}")
    
    def _parse_final_classification_packet(self, data, header):
        """解析Final Classification数据包"""
        if not self._should_collect('final_classification'):
            return
        
        timestamp = time.time()
        offset = 30
        
        try:
            for car_idx in range(MAX_CARS):
                car_format = '<BBBBBBBIdBBBBBBBBBBBBBBBBBBBBBBBBBBB'
                car_size = struct.calcsize(car_format)
                if offset + car_size > len(data):
                    break
                
                car_data = struct.unpack(car_format, data[offset:offset + car_size])
                
                row = [
                    timestamp, header['session_uid'], header['frame_identifier'], car_idx ,
                    car_data[0],car_data[1],car_data[2],car_data[3],    #position, num_laps, grid_position, points
                    car_data[4],car_data[5],car_data[6],car_data[7],    #num_pit_stops, result_status, result_reason, best_lap_time_ms
                    car_data[8],car_data[9],car_data[10],car_data[11]   #total_race_time, penalties_time, num_penalties, num_tyre_stints
                    ]
                self.csv_writers['final_classification'].writerow(row)
                offset += car_size
        except (struct.error, IndexError) as e:
            print(f"解析Final Classification数据错误: {e}")

    def _parse_participants_packet(self, data, header):
        """解析Participants数据包"""
        if not self._should_collect('participants'):
            return

        timestamp = time.time()
        offset = 30  # Header size

        try:
            if len(data) < offset + 1:
                return

            m_numActiveCars = struct.unpack_from('<B', data, offset)[0]
            offset += 1

            participant_format = '<BBBBBBB32sBBHBBBBBBBBBBBBBB'  # up to m_numColours
            participant_size = struct.calcsize(participant_format)

            for car_idx in range(MAX_CARS):
                if offset + participant_size > len(data):
                    break

                participant_data = struct.unpack_from(participant_format, data, offset)
                offset += participant_size
                
                # Clean and decode m_name field
                m_name = participant_data[7].split(b'\x00', 1)[0].decode('utf-8', errors='replace')

                row = [
                    timestamp,header['session_uid'],header['frame_identifier'],car_idx,
                    participant_data[0],participant_data[1],participant_data[2],participant_data[3],#ai_controlled, driver_id, network_id, team_id
                    participant_data[4],participant_data[5],participant_data[6],m_name,#my_team, race_number, nationality, name
                    participant_data[8],participant_data[9],participant_data[10],participant_data[11]#your_telemetry, show_online_names, tech_level, platform
                ]

                self.csv_writers['participants'].writerow(row)

        except (struct.error, IndexError, UnicodeDecodeError) as e:
            print(f"解析Participants数据错误: {e}")
    
    def process_packet(self, data):
        """处理接收到的数据包"""
        try:
            header, header_size = self._parse_header(data)

            if header is None:
                return

            # 更新session UID
            if self.session_uid is None:
                self.session_uid = header['session_uid']
                print(f"开始新会话: {self.session_uid}")

            packet_id = header['packet_id']
            # 根据packet类型调用相应的解析函数
            if packet_id == PacketID.MOTION:
                self._parse_motion_packet(data, header)
            elif packet_id == PacketID.SESSION:
                self._parse_session_packet(data, header)
            elif packet_id == PacketID.LAP_DATA:
                self._parse_lap_data_packet(data, header)
            elif packet_id == PacketID.CAR_TELEMETRY:
                self._parse_telemetry_packet(data, header)
            elif packet_id == PacketID.CAR_STATUS:
                self._parse_car_status_packet(data, header)
            elif packet_id == PacketID.CAR_DAMAGE:
                self._parse_car_damage_packet(data, header)
            elif packet_id == PacketID.CAR_SETUPS:
                self._parse_car_setups_packet(data, header)
            elif packet_id == PacketID.MOTION_EX:
                self._parse_motion_ex_packet(data, header)
            elif packet_id == PacketID.FINAL_CLASSIFICATION:
                self._parse_final_classification_packet(data, header)
            elif packet_id == PacketID.PARTICIPANTS:
                self._parse_participants_packet(data, header)

        except Exception as e:
            print(f"处理数据包时出错: {e}")

    def start_collecting(self):
        """开始收集数据"""
        self.running = True
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('', self.port))
        sock.settimeout(1.0)

        print(f"开始监听UDP端口 {self.port}...")
        print("等待F1 25游戏数据...")
        print(f"数据采集间隔: {COLLECTION_INTERVAL}秒")
        print("按Ctrl+C停止收集")

        packet_count = 0
        try:
            while self.running:
                try:
                    data, addr = sock.recvfrom(8192)  # 增加缓冲区大小
                    self.process_packet(data)
                    packet_count += 1

                    # 每100个包显示一次状态
                    if packet_count % 100 == 0:
                        print(f"已处理 {packet_count} 个数据包...")
                        # 定期刷新文件
                        for file in self.csv_files.values():
                            file.flush()

                except socket.timeout:
                    continue
        except KeyboardInterrupt:
            print(f"\n收集已停止，共处理 {packet_count} 个数据包")
        finally:
            sock.close()
            self.close()

    def close(self):
        """关闭所有CSV文件"""
        print("正在保存数据...")
        for file in self.csv_files.values():
            file.close()
        print("数据已保存完成!")


if __name__ == "__main__":
    print("=" * 60)
    print("F1 25 遥测数据收集器")
    print("=" * 60)
    print("\n使用说明:")
    print("1. 确保F1 25游戏已启动")
    print("2. 在游戏设置中启用UDP遥测输出")
    print("3. 设置UDP端口为20777(或修改代码中的端口)")
    print("4. 运行此程序后开始游戏")
    print("5. 数据将自动保存到 'f1_telemetry_data' 文件夹")
    print(f"6. 数据采集间隔: {COLLECTION_INTERVAL}秒\n")

    # 创建收集器实例
    collector = F1TelemetryCollector()

    # 开始收集数据
    collector.start_collecting()