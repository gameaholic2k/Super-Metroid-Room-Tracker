import glob
import json
import copy
import csv
import statistics
from datetime import datetime
from pathlib import Path
import file_loader

class RunCategory():
    def __init__(self, run_category):
        self.config = file_loader.FileManager()
        self.run_category = run_category
        self.run_category_room_paths = self.get_run_category_room_paths()
        self.room_time_names = self.get_room_time_names()
        # Must be initialized by the SuperMetroidRooms class as it contains the compare room and log methods to build the index

        self.run_category_indexes = None
        self.fastest_room_times = None
        self.average_room_times = None

    def get_run_category_filename(self) -> str:
        '''
        Gets the filename from the run category
        :return:
        '''
        file_paths = []
        json_files = glob.glob(f'{self.config.run_category_directory}/*.json')
        for file in json_files:
            try:
                with open(file, 'r') as f:
                    category_definition = json.load(f)
                if category_definition['category'] == self.run_category:
                    return file
            except Exception as e:
                print(f'Exception encountered from reading file: {file}')
                raise e
        raise RuntimeError(f'No category "{self.run_category}" found in any of the files under "{self.config.run_category_directory}"')
    
    def get_run_category_index_filename(self):
        '''
        Gets the file name of the run category index csv file
        :return: Index filename
        '''
        return f'{self.run_category}_index.csv'
    
    def get_run_category_room_paths(self) -> dict:
        '''

        :return:
        '''
        with open(self.get_run_category_filename(), 'r') as f:
            run_category_room_paths = json.load(f)['roomDefinitionList']

        with open(self.config.pre_defined_room_states_file, 'r') as f:
            pre_defined_room_states = json.load(f)

        # updated_run_category_room_path = []
        for room_path in run_category_room_paths:
            if not 'not_yet_implemented' in room_path:
                entry_loadout_key = room_path['entry_loadout']
                exit_loadout_key = room_path['exit_loadout']

                pre_defined_entry = pre_defined_room_states[entry_loadout_key]
                pre_defined_exit = pre_defined_room_states[exit_loadout_key]

                entry_collected_items = pre_defined_entry['collectedItems']
                exit_collected_items = pre_defined_exit['collectedItems']

                # Moving collected items to its own definition as we need to process that info separately
                entry_predefined = {key: copy.deepcopy(value) for key, value in pre_defined_entry.items() if key != 'collectedItems'}
                exit_predefined = {key: copy.deepcopy(value) for key, value in pre_defined_exit.items() if key != 'collectedItems'}

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

                # updated_run_category_room_path.append(room_path)
        return run_category_room_paths
        # return updated_run_category_room_path

    def get_room_time_names(self) -> list:
        '''

        :return:
        '''
        rooms = []
        for room in self.run_category_room_paths:
            rooms.append(room['names']['individual_room_time_name'])
        return rooms

class SuperMetroidRooms():
    def __init__(self):
        self.sm_files = file_loader.FileManager()
        self.run_categories = self._get_run_categories()
        self.room_logs = self.sm_files.get_room_logs()
        self.sm_address_data = self.sm_files.get_address_definitions()
        self._initialize_run_category_indexes()
    
    # Private methods
    def _get_run_categories(self):
        '''

        :return:
        '''
        # run_categories = []
        run_categories = {}
        for category in self.sm_files.get_run_categories():
            # run_categories.append(RunCategory(category))
            run_categories[category] = RunCategory(category)
        return run_categories
    

    # Public methods
    def is_subset_dict(self, subset_dict, superset_dict):
        '''
        Checks if the subsect dict is part of a superset dict, used to compare a room path logic to a room log
        :param subset_dict: subsect dic (typically theroom logic definition)
        :param superset_dict: supersec dict (typically the room log)
        :return:
        '''
        def flatten_dict(d, parent_key='', sep='_'):
            items = []
            for k, v in d.items():
                new_key = parent_key + sep + k if parent_key else k
                if isinstance(v, dict):
                    items.extend(flatten_dict(v, new_key, sep=sep).items())
                else:
                    items.append((new_key, v))
            return dict(items)

        #Flattens the dictionary to compare all of the nested values
        flattened_subset_dict = flatten_dict(subset_dict)
        flattened_uperset_dict = flatten_dict(superset_dict)

        for item in flattened_subset_dict.items():
            if not item in flattened_uperset_dict.items():
                return False
        return True
    
    def compare_room_data(self, room_path_logic, room_log) -> bool:
        if "not_yet_implemented" in room_path_logic:
            return False
        
        data_match = self.is_subset_dict(room_path_logic['data'], room_log['data'])

        #Matching enemies killed:
        items_match = self.compare_collected_items(room_path_logic, room_log)
        if "lessThanEnemiesKilled" in room_path_logic:
            if room_log['data']['enemiesKilled'] >= room_path_logic['lessThanEnemiesKilled']:
                return False
        
        if "greaterThanorEqualEnemiesKilled" in room_path_logic:
            if room_log['data']['enemiesKilled'] < room_path_logic['greaterThanorEqualEnemiesKilled']:
                return False

        return all(x == True for x in [data_match, items_match])
    
    def compare_collected_items(self, room_definition, room_log):
        '''
        Performs a bit mask check on collected items to verify if the item was collected
        :param room_definition:
        :param room_log:
        :return:
        '''
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
                        # if debug:
                        #     print(f'Item: {item} not found')
                        return False
            return True

        entry_collected_items = room_definition['entryCollectedItems']
        exit_collected_items = room_definition['exitCollectedItems']
        room_log_entry_state_items = room_log['data']['entryState']['collectedItems']
        room_log_exit_state_items = room_log['data']['exitState']['collectedItems']

        entry_match = compare_item_lists(entry_collected_items, room_log_entry_state_items)
        exit_match = compare_item_lists(exit_collected_items, room_log_exit_state_items)
        return all(x is True for x in [entry_match, exit_match])
    
    def get_times_from_room_path(self, room_path_logic):
        '''

        :param room_path_logic:
        :return:
        '''
        times = []
        for log in self.room_logs:
            if not "not_yet_implemented" in room_path_logic:
                if self.compare_room_data(room_path_logic, log):
                    # times.append(log['data']['frameCount'])
                    times.append(log['data']['practiceFrames'])
        return times
    
    def get_room_name_with_address(self, hex_address):
        '''

        :param hex_address:
        :return:
        '''
        for room in self.sm_address_data:
            if hex_address.upper() == room["value"].upper():
                return room["name"]
            
    def _initialize_run_category_indexes(self):
        '''

        :return:
        '''
        for category in self.run_categories.values():
            index_filename = category.get_run_category_index_filename()
            if not Path(index_filename).exists():
                self.rebuild_run_category_index(category)
            else:

                room_log_indexes = []
                with open(index_filename, mode='r', newline='') as file:
                    reader = csv.reader(file)
                    for row in reader:
                        room_log_indexes.append(row)
                # return room_log_indexes
                category.run_category_indexes = room_log_indexes

    def get_log_indexes_from_room_definition(self, room_path_logic):
        '''

        :param room_path_logic:
        :return:
        '''
        room_log_indexes = []
        for index, log in enumerate(self.room_logs):
            # print(room_path_logic)
            # print(log)
            if self.compare_room_data(room_path_logic, log) is True:
                room_log_indexes.append(index)
        return room_log_indexes

    def rebuild_run_category_index(self, run_category):
        '''

        :param run_category:
        :return:
        '''
        room_log_indexes = []
        counter = 0
        num_of_rooms = len(run_category.run_category_room_paths)
        for room_path in run_category.run_category_room_paths:
            room_log_index = self.get_log_indexes_from_room_definition(room_path)
            if room_log_index:
                room_log_indexes.append(room_log_index)
            else:
                # room_log_indexes.append([[]])
                room_log_indexes.append([])
            counter += 1
            print(f'{(counter / num_of_rooms)*100}% Complete')

        index_file = run_category.get_run_category_index_filename()
        with open(index_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(room_log_indexes)
        run_category.run_category_indexes = room_log_indexes

    def get_room_times_from_index(self, run_category):
        '''

        :param run_category:
        :return:
        '''
        room_times = []
        for log_index_list in run_category.run_category_indexes:
            if not any(item == [] for item in log_index_list):
                room_times.append([self.room_logs[int(idx)]['data']['practiceFrames'] for idx in log_index_list])
            else:
                room_times.append([])
        return room_times
    
    def get_fastest_room_times(self, run_category):
        '''

        :param run_category:
        :return:
        '''
        room_times_table = []
        frame_data_table = self.get_room_times_from_index(run_category)
        for room_times in frame_data_table:
            if room_times:
                fastest_time = min(room_times)
                formatted_time = convert_framecount_to_seconds(fastest_time)
            else:
                formatted_time = ''
            room_times_table.append(formatted_time)
        return room_times_table

    def get_average_room_times(self, run_category):
        '''

        :param run_category:
        :return:
        '''
        room_times_table = []
        frame_data_table = self.get_room_times_from_index(run_category)
        for room_times in frame_data_table:
            if room_times:
                average_time = round(statistics.mean(room_times))
                formatted_time = convert_framecount_to_seconds(average_time)
            else:
                formatted_time = ''
            room_times_table.append(formatted_time)
        return room_times_table

    def get_run_category_room_logic_index(self, room_log, run_category):
        '''

        :param room_log:
        :param run_category:
        :return:
        '''

        for index, room_path_logic in enumerate(run_category.run_category_room_paths):
            if self.compare_room_data(room_path_logic, room_log) is True:
                return index


def convert_framecount_to_seconds(framecount):
    '''

    :param framecount:
    :return:
    '''
    if not framecount:
        return None
    seconds = int(framecount / 60)
    remainder_frames = framecount % 60
    return f'{seconds}.{str(remainder_frames).zfill(2)}'


def convert_room_time_to_framecount(room_time):
    '''

    :param framecount:
    :return:
    '''
    if not room_time:
        return None
    seconds, frames = map(int, room_time.split('.'))
    total_frames = seconds * 60 + frames
    return total_frames

