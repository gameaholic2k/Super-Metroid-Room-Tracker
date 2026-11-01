import glob
import json
import copy
import csv
import os
import statistics
from pathlib import Path
import file_loader
import logging
import bisect
import shutil
import time
import datetime
# from datetime import timedelta, timezone
from dataclasses import dataclass
from typing import Final, Any
import default_file_generator
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

def write_csv_file(csv_file_path, csv_data):
    while True:
        try:
            with open(csv_file_path, mode='w', newline='') as csv_file_handler:
                writer = csv.writer(csv_file_handler)
                # if nested list
                if any(isinstance(item, list) for item in csv_data):
                    writer.writerows(csv_data)
                else:
                    writer.writerow(csv_data)
                return
        except PermissionError:
            logger.info(f"\n[Error] Permission denied: Cannot write to '{csv_file_path}'.")
            logger.info("Please close the file if it is open in another program.")

            # Wait for user confirmation before retrying
            logger.info("Press any key to try again...")
            logger.info("Retrying...\n")

def _is_subset_dict(subset_dict, superset_dict):
    """
    Checks if the subsect dict is part of a superset dict, used to compare a room path logic to a room log
    :param subset_dict: subsect dic (typically the room logic definition)
    :param superset_dict: supersec dict (typically the room log)
    :return:
    """
    def flatten_dict(d, parent_key='', sep='_'):
        items = []
        for k, v in d.items():
            new_key = parent_key + sep + k if parent_key else k
            if isinstance(v, dict):
                items.extend(flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)

    # Flattens the dictionary to compare all the nested values
    flattened_subset_dict = flatten_dict(subset_dict)
    flattened_superset_dict = flatten_dict(superset_dict)

    for item in flattened_subset_dict.items():
        if not item in flattened_superset_dict.items():
            return False
    return True

def convert_framecount_to_seconds(framecount):
    """

    :param framecount:
    :return:
    """
    seconds = int(framecount / 60)
    remainder_frames = framecount % 60
    return f'{seconds}.{str(remainder_frames).zfill(2)}'


def convert_room_time_to_framecount(room_time):
    """

    :param room_time:
    :return:
    """
    if not room_time:
        return None
    seconds, frames = map(int, room_time.split('.'))
    total_frames = seconds * 60 + frames
    return total_frames

@dataclass
class Logs:
    practice_log_path: Path
    vanilla_log_path: Path
    practice_logs: list[dict[str, str]]
    vanilla_logs: list[dict[str, str]]

class RoomLogs:
    def __init__(self, sm_files, enabled_run_categories):
        self.current_session_start_time = time.time()
        self.sm_files = sm_files
        self.logs = Logs(practice_log_path=self.sm_files.room_log_practice_file,
                         vanilla_log_path=self.sm_files.room_log_vanilla_file,
                         practice_logs= self.sm_files.get_room_logs(is_practice_rom=True),
                         vanilla_logs= self.sm_files.get_room_logs(is_practice_rom=False)
                         )

        self.run_category_instances = {}
        for name in enabled_run_categories:
            self.add_category_instance(name)

    def add_category_instance(self, category_name):
        self.run_category_instances[category_name] = RunCategory(category_name=category_name,
                                                            logs=self.logs,
                                                            sm_files=self.sm_files)
    def backup_logs(self):
        backup = self.sm_files.room_log_practice_file.with_name(self.sm_files.room_log_practice_file.name + '.bak')
        shutil.copy2(self.sm_files.room_log_practice_file, backup)
        logger.info(f"Backed up '{self.sm_files.room_log_practice_file.name}' to '{backup.name}'")

    def update_item_collection_times(self):
        is_log_file_edited = False
        for index, room in enumerate(self.logs.practice_logs):
            entry_collected_items = room['data']['entryState']['collectedItems']
            exit_collected_items = room['data']['exitState']['collectedItems']
            if entry_collected_items != exit_collected_items:
                fanfare_frames = 328
                frame_offset = 28
                frame_count = room["data"]["frameCount"]
                practice_frames = room["data"]["practiceFrames"]
                frame_differences = practice_frames - frame_count
                logger.info(f'Log Index: {index}')
                logger.info(f'Real time frame count: {frame_count}')
                logger.info(f'Practice frame count:  {practice_frames}')
                logger.info(f'Frame differences: {frame_differences}')
                # Adds the fanfare frames if the practice times are close to real time
                if frame_differences < fanfare_frames - frame_offset and frame_differences > -frame_offset:
                    new_practice_frame_count = practice_frames + fanfare_frames
                    logger.info(f'Updating practice frame count from {practice_frames} to {new_practice_frame_count}')
                    self.logs.practice_logs[index]["data"]["practiceFrames"] = new_practice_frame_count
                    is_log_file_edited = True
                print('\n')

        if is_log_file_edited is True:
            logger.info(f'Writing to Log {self.sm_files.get_relative_path(self.sm_files.room_log_practice_file)}')
            self.backup_logs()
            with open(self.sm_files.room_log_practice_file, 'w') as log_handler:
                for entry in self.logs.practice_logs:
                    log_handler.write(json.dumps(entry) + "\n")

            for category_instance in self.run_category_instances.values():
                category_instance.rebuild_run_category_index(is_practice_rom=True, logs=self.logs)

            logger.info('Finished updating room collection times.')
        else:
            logger.info('No changes made to the logs from rooms with item collection')

    def update_room_logs(self, is_practice_rom):
        if is_practice_rom:
            self.logs.practice_logs = self.sm_files.get_room_logs(is_practice_rom=True)
        else:
            self.logs.vanilla_logs = self.sm_files.get_room_logs(is_practice_rom=False)

    def get_current_session_logs(self, is_practice_rom:bool) -> list[dict]:
        if is_practice_rom:
            logs = self.logs.practice_logs
        else:
            logs = self.logs.vanilla_logs
        return [d['data'] for d in logs if 'timestamp' in d and d['timestamp'] > self.current_session_start_time]

    def get_weekly_logs(self, is_practice_rom:bool, logs=None) -> list[dict]:
        now = datetime.datetime.now()
        days_since_sunday = int(now.strftime('%w'))
        start_of_week = (now - datetime.timedelta(days=days_since_sunday)).replace(hour=0, minute=0, second=0, microsecond=0)
        start_of_week_timestamp = start_of_week.timestamp()
        if logs is None:
            if is_practice_rom:
                logs = self.logs.practice_logs
            else:
                logs = self.logs.vanilla_logs

        return [d['data'] for d in logs if 'timestamp' in d and d['timestamp'] > start_of_week_timestamp]


    def get_monthly_logs(self, is_practice_rom:bool, logs=None) -> list[dict]:
        now = datetime.datetime.now()
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        start_of_month_timestamp = start_of_month.timestamp()
        if logs is None:
            if is_practice_rom:
                logs = self.logs.practice_logs
            else:
                logs = self.logs.vanilla_logs
        return [d['data'] for d in logs if 'timestamp' in d and d['timestamp'] > start_of_month_timestamp]


    def get_days_ago_logs(self, is_practice_rom:bool, days:int, logs=None) -> list[dict]:
        now = datetime.datetime.now()
        days_ago = now - datetime.timedelta(days=days)
        days_ago_timestamp = days_ago.timestamp()
        if logs is None:
            if is_practice_rom:
                logs = self.logs.practice_logs
            else:
                logs = self.logs.vanilla_logs
        return[d['data'] for d in logs if 'timestamp' in d and d['timestamp'] > days_ago_timestamp]

class RunCategory:
    def __init__(self, category_name: str, logs: Logs, sm_files: file_loader.FileManager):
        self.category_name: Final[str] = category_name
        self.config = file_loader.FileManager()
        self.sm_address_data: Final[dict] = sm_files.get_address_definitions()
        self.room_definitions = self.merge_room_definition_data()
        self.run_category_indexes_practice = self._initialize_run_category_index(is_practice_rom=True, logs=logs)
        self.run_category_indexes_vanilla = self._initialize_run_category_index(is_practice_rom=False, logs=logs)
        self.room_time_names = self.get_room_time_names()
        self.user_room_data = self.get_run_category_user_data()

    def get_room_time_names(self) -> list:
        """

        :return:
        """
        rooms = []
        for room in self.room_definitions:
            rooms.append(room['names']['individual_room_time_name'])
        return rooms

    # Get filenames/paths
    def get_run_category_filename(self) -> str:
        """
        Gets the filename from the run category
        :return:
        """
        json_files = glob.glob(f'{self.config.run_category_directory}/*.json')
        for file in json_files:
            try:
                with open(file, 'r') as f:
                    category_definition = json.load(f)
                if category_definition['category'] == self.category_name:
                    return file
            except Exception as e:
                print(f'Exception encountered from reading file: {file}')
                raise e
        raise RuntimeError(f'No category "{self.category_name}" found in any of the files under '
                           f'"{self.config.run_category_directory}"')


    def get_run_category_index_filepath(self, is_practice_rom) -> Path:
        """
        Gets the file name of the run category index csv file
        :return: Index filename
        """
        if is_practice_rom:
            return Path(os.path.join(self.config.index_directory, f'{self.category_name}_practice_index.csv'))
        else:
            return Path(os.path.join(self.config.index_directory, f'{self.category_name}_vanilla_index.csv'))


    def get_run_category_index_undefined_filepath(self, is_practice_rom) -> Path:
        """
        Gets the file name of the run category index csv file
        :return: Index filename
        """
        if is_practice_rom:
            return Path(os.path.join(self.config.index_directory, f'{self.category_name}_undefined_practice_index.csv'))
        else:
            return Path(os.path.join(self.config.index_directory, f'{self.category_name}_undefined_vanilla_index.csv'))


    def merge_room_definition_data(self) -> dict:
        """

        :return:
        """
        with open(self.get_run_category_filename(), 'r') as f:
            run_category_room_paths = json.load(f)['roomDefinitionList']

        with open(self.config.pre_defined_room_states_file, 'r') as f:
            pre_defined_room_states = json.load(f)

        for room_path in run_category_room_paths:
            if not 'not_yet_implemented' in room_path:
                entry_loadout_key = room_path['entry_loadout']
                exit_loadout_key = room_path['exit_loadout']

                pre_defined_entry = pre_defined_room_states[entry_loadout_key]
                pre_defined_exit = pre_defined_room_states[exit_loadout_key]

                entry_collected_items = pre_defined_entry['collectedItems']
                exit_collected_items = pre_defined_exit['collectedItems']

                # Moving collected items to its own definition as we need to process that info separately
                entry_predefined = {key: copy.deepcopy(value) for key, value in pre_defined_entry.items() if
                                    key != 'collectedItems'}
                exit_predefined = {key: copy.deepcopy(value) for key, value in pre_defined_exit.items() if
                                   key != 'collectedItems'}

                if 'entryState' in room_path['data']:
                    merged_entry_state = entry_predefined | room_path['data']['entryState']
                else:
                    merged_entry_state = entry_predefined

                if 'exitState' in room_path['data']:
                    merged_exit_state = exit_predefined | room_path['data']['exitState']
                else:
                    merged_exit_state = exit_predefined

                room_path['data']['entryState'] = merged_entry_state
                room_path['data']['exitState'] = merged_exit_state
                room_path['entryCollectedItems'] = entry_collected_items
                room_path['exitCollectedItems'] = exit_collected_items

        return run_category_room_paths


    def _initialize_run_category_index(self, is_practice_rom: bool, logs: Logs):
        """

        :return:
        """

        index_filename = self.get_run_category_index_filepath(is_practice_rom)
        print(f'Getting index from {index_filename}')
        if not Path(index_filename).exists():
            return self.get_rebuild_run_category_index(is_practice_rom, logs)
        else:
            room_log_indexes = []
            with open(index_filename, mode='r', newline='') as file:
                reader = csv.reader(file)
                for row in reader:
                    room_log_indexes.append(row)

            return room_log_indexes

    def get_rebuild_run_category_index(self, is_practice_rom: bool, logs: Logs):
        num_of_room_paths = len(self.room_definitions)


        room_log_indexes: list[list[int]] = [[] for _ in range(num_of_room_paths)]
        undefined_room_paths = []
        if is_practice_rom:
            room_logs = logs.practice_logs
            time_key = 'practiceFrames'
        else:
            room_logs = logs.vanilla_logs
            time_key = 'frameCount'

        index_filename = Path(self.get_run_category_index_filepath(is_practice_rom)).name
        num_of_logs = len(room_logs)
        counter = 0
        if num_of_logs > 0:
            last_build_percentage_progress = int((counter / num_of_logs) * 100)
        else:
            last_build_percentage_progress = 0
        for log_index, log in enumerate(room_logs):
            room_path_logic_index = self.get_run_category_room_definition_index(log)
            if room_path_logic_index is not None:
                # Get index to plug in the new index data by sorting the timed data
                if room_log_indexes[room_path_logic_index]:
                    # Create a temp list of room times from the category index
                    room_times = [room_logs[int(index)]['data'][time_key] for index in
                                  room_log_indexes[room_path_logic_index]]
                    new_room_time = room_logs[log_index]['data'][time_key]
                    index_to_insert = bisect.bisect_left(room_times, new_room_time)
                    room_log_indexes[room_path_logic_index].insert(index_to_insert, log_index)
                else:
                    room_log_indexes[room_path_logic_index].append(log_index)

            else:
                undefined_room_paths.append(log_index)
            counter += 1
            current_build_percentage_progress = int((counter / num_of_logs) * 100)
            if last_build_percentage_progress != current_build_percentage_progress:
                print(f'Rebuilding {index_filename}: {current_build_percentage_progress}% Complete')
                last_build_percentage_progress = current_build_percentage_progress

        index_file = self.get_run_category_index_filepath(is_practice_rom)
        write_csv_file(csv_file_path=index_file, csv_data=room_log_indexes)

        undefined_index_file = self.get_run_category_index_undefined_filepath(is_practice_rom)
        write_csv_file(csv_file_path=undefined_index_file, csv_data=undefined_room_paths)

        return room_log_indexes


    def rebuild_run_category_index(self, is_practice_rom: bool, logs: Logs):
        """
        Wrapper to build the index and apply the changes to the relevant index
        :param is_practice_rom:
        :param logs:
        :return:
        """
        if is_practice_rom:
            self.run_category_indexes_practice = self.get_rebuild_run_category_index(is_practice_rom, logs)
        else:
            self.run_category_indexes_vanilla = self.get_rebuild_run_category_index(is_practice_rom, logs)

    def get_run_category_room_definition_index(self, room_log):
        for index, room_path_logic in enumerate(self.room_definitions):
            if self.compare_room_data(room_path_logic, room_log) is True:
                return index
        return None

    def compare_room_data(self, room_path_logic, room_log) -> bool:
        if "not_yet_implemented" in room_path_logic:
            return False

        # Add shinesparked false flag if it's not in the log
        if room_path_logic['data'].get('shinesparked') is False:
            if 'shinesparked' not in room_log['data']:
                room_log['data']['shinesparked'] = False

        data_match = _is_subset_dict(room_path_logic['data'], room_log['data'])

        # Matching enemies killed:
        items_match = self.compare_collected_items(room_path_logic, room_log)
        if "lessThanEnemiesKilled" in room_path_logic:
            if room_log['data']['enemiesKilled'] >= room_path_logic['lessThanEnemiesKilled']:
                return False

        if "greaterThanorEqualEnemiesKilled" in room_path_logic:
            if room_log['data']['enemiesKilled'] < room_path_logic['greaterThanorEqualEnemiesKilled']:
                return False

        return all(x == True for x in [data_match, items_match])


    def compare_collected_items(self, room_definition, room_log):
        """
        Performs a bit mask check on collected items to verify if the item was collected
        :param room_definition:
        :param room_log:
        :return:
        """
        def compare_item_lists(definition_collected_items, room_log_item_state):

            if not definition_collected_items:
                if all(x == 0 for x in room_log_item_state):
                    return True
                else:
                    return False

            else:
                item_data = None
                base_index = int('0xD870', 16)
                for item in definition_collected_items:
                    for address_data in self.sm_address_data:
                        if address_data['name'] == item:
                            item_data = address_data
                            break
                    if not item_data:
                        return False
                    address = int(item_data['address'], 16)
                    value = int(item_data['value'], 16)
                    index = address - base_index
                    if not room_log_item_state[index] & value:
                        return False
            return True

        entry_collected_items = room_definition['entryCollectedItems']
        exit_collected_items = room_definition['exitCollectedItems']
        room_log_entry_state_items = room_log['data']['entryState']['collectedItems']
        room_log_exit_state_items = room_log['data']['exitState']['collectedItems']

        entry_match = compare_item_lists(entry_collected_items, room_log_entry_state_items)
        exit_match = compare_item_lists(exit_collected_items, room_log_exit_state_items)
        return all(x is True for x in [entry_match, exit_match])

    def get_number_of_index_entries_from_index_files(self, is_practice_rom: bool):
        index_file = self.get_run_category_index_filepath(is_practice_rom)
        index_row_entries = 0
        with open(index_file, mode='r') as index_file_handler:
            index_reader = csv.reader(index_file_handler)
            for row in index_reader:
                index_row_entries += sum(1 for cell in row if cell.strip() != '')

        index_undefined_entries = 0
        index_undefined_file = self.get_run_category_index_undefined_filepath(is_practice_rom)
        if Path(index_undefined_file).exists():
            with open(index_undefined_file, mode='r') as index_undefined_file_handler:
                index_undefined_reader = csv.reader(index_undefined_file_handler)
                # index_undefined_entries = sum(1 for row in index_undefined_reader)
                for row in index_undefined_reader:
                    index_undefined_entries += sum(1 for cell in row if cell.strip() != '')

        number_of_total_index_entries = index_row_entries + index_undefined_entries

        return number_of_total_index_entries


    def get_room_times_table_from_index_data(self, room_logs: list[dict[str,str]], is_practice_rom: bool, log_index_start: int):
        if is_practice_rom:
            run_category_indexes = self.run_category_indexes_practice
            time_key = 'practiceFrames'
        else:
            run_category_indexes = self.run_category_indexes_vanilla
            time_key = 'frameCount'

        room_times: list[list] = []

        run_category_idx: int
        for run_category_idx, log_index_list in enumerate(run_category_indexes):
            if not any(item == [] for item in log_index_list):
                try:
                    room_times.append([room_logs[int(idx)]['data'][time_key] for idx in log_index_list if int(idx) >= log_index_start] )

                except IndexError as e:
                    logger.exception(time_key)
                    logger.exception(e)
                    logger.exception(f'Length of room logs: {len(room_logs)}')
                    logger.exception(log_index_list)
                    raise IndexError(e)

            else:
                room_times.append([])
        return room_times


    # Calculate room time methods
    def get_fastest_room_times_table(self, logs: list[dict[str, str]], is_practice_rom: bool, log_index_start: int):
        room_times_table = []
        frame_data = self.get_room_times_table_from_index_data(logs, is_practice_rom, log_index_start)
        for room in range(len(frame_data)):
            if frame_data[room]:
                fastest_time = min(frame_data[room])
                formatted_time = convert_framecount_to_seconds(fastest_time)
            else:
                formatted_time = ''
            room_times_table.append(formatted_time)
        return room_times_table


    def get_average_room_times_table(self, logs: list[dict[str, str]], is_practice_rom, log_index_start: int):
        room_times_table = []
        frame_data = self.get_room_times_table_from_index_data(logs, is_practice_rom, log_index_start)
        for room in range(len(frame_data)):
            if frame_data[room]:
                average_time = round(statistics.mean(frame_data[room]))
                formatted_time = convert_framecount_to_seconds(average_time)
            else:
                formatted_time = ''
            room_times_table.append(formatted_time)
        return room_times_table

    def get_run_category_room_logic_index(self, room_log_entry):
        for index, room_path_logic in enumerate(self.room_definitions):
            if self.compare_room_data(room_path_logic, room_log_entry) is True:
                return index
        return None

    def get_run_category_user_data(self):
        user_data_filepath = Path(os.path.join(self.config.user_data_folder_path, f'{self.category_name}_user_data.json'))
        if not user_data_filepath.exists():
            with open(self.get_run_category_filename(), 'r') as f:
                category_definition = json.load(f)
            user_room_data = default_file_generator.generate_user_data(category_definition)
            with open(user_data_filepath, "w") as file:
                json.dump(user_room_data, file, indent=4)
            return user_room_data

        else:
            with open(user_data_filepath, 'r') as file_handler:
                user_room_data = json.load(file_handler)
            return user_room_data