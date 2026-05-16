import json
import glob
from pathlib import Path
import configparser
from typing import Final
# from dataclasses import dataclass
#
# @dataclass
# class DefaultConfig:
#     room_log_file: str = 'list_of_roomtimes.jsonl'
#     run_category_directory: str = 'categories'
#     address_file: str = 'SuperMetroid.json'
#     room_log_directory: str = 'logs'
#     pre_defined_room_states_file: str = 'pre_defined_room_states.json'
#     channel_name: str = ''
#     api_token: str = ''
#
#     # GUI config entries
#     window_size: str = '1100x760'
#     min_horizontal_size: int = 780
#     min_vertical_size: int = 620
#     default_run_category: str = 'KPDR'





class FileManager:
    DEFAULT_CATEGORY_KEY: Final = 'default_run_category'

    def __init__(self):
        self._config_file = 'config.ini'
        self.config = self.initialize_config()
        self.roomtime_config = self.config['roomtime_config']
        self.gui_config = self.config['gui_config']

    @property
    def config_file(self):
        return self._config_file

    @property
    def room_log_file(self):
        return self.roomtime_config['room_log_file']

    @property
    def run_category_directory(self):
        return self.roomtime_config['category_folder']

    @property
    def _address_file(self):
        return self.roomtime_config['address_file']

    @property
    def room_log_directory(self):
        return self.roomtime_config['room_log_file_folder']

    @property
    def pre_defined_room_states_file(self):
        return self.roomtime_config['pre_defined_room_states_file']

    @property
    def channel_name(self):
        return self.roomtime_config['channel_name']

    @property
    def api_token(self):
        return self.roomtime_config['api_token']

    # GUI properties
    @property
    def window_size(self):
        return self.gui_config['window_size']

    @property
    def min_horizontal_size(self):
        return self.gui_config['min_horizontal_size']

    @property
    def min_vertical_size(self):
        return self.gui_config['min_vertical_size']

    def initialize_config(self):
        config = configparser.ConfigParser()

        if not Path(self._config_file).exists():
            config['roomtime_config'] = {
                'room_log_file': 'list_of_roomtimes.jsonl',
                'category_folder': 'categories',
                'address_file': 'SuperMetroid.json',
                'pre_defined_room_states_file': 'pre_defined_room_states.json',
                'room_log_file_folder': 'logs',
                'channel_name': '',
                'api_token': '',
                'default_run_category': ''
            }
            config['gui_config'] = {
                'window_size': '1100x760',
                'min_horizontal_size': '780',
                'min_vertical_size': '620'
            }

            with open(self._config_file, 'w') as config_file:
                config.write(config_file)

        config.read(self._config_file)
        return config

    def get_run_category_files(self):
        '''

        :return:
        '''
        json_files = glob.glob(f'{self.run_category_directory}/*.json')
        return json_files

    def get_default_run_category(self):
        default_category_config = self.roomtime_config[self.DEFAULT_CATEGORY_KEY]
        if not default_category_config:
            first_category = self.get_run_categories()[0]
            self.roomtime_config[self.DEFAULT_CATEGORY_KEY] = first_category
            with open(self.config_file, 'w') as file_handler:
                self.config.write(file_handler)
            return first_category
        else:
            return default_category_config

    def get_run_categories(self):
        run_categories = []
        run_category_files = self.get_run_category_files()
        for file in run_category_files:
            try:
                with open(file, 'r') as f:
                    category_definition = json.load(f)
                    run_categories.append(category_definition['category'])
            except Exception as e:
                print(f'Exception encountered from reading file: {file}')
                raise e
        return run_categories
    
    def get_room_logs(self):
        '''

        :return:
        '''
        data = []
        if not Path(self.room_log_file).exists():
            with open(self.room_log_file, 'w') as f:
                pass
        with open(self.room_log_file, 'r') as f:
            for line in f:
                data.append(json.loads(line))
        return data
    
    def get_address_definitions(self):
        '''

        :return:
        '''
        with open(self._address_file, 'r') as f:
            address_definitions = json.load(f)['definitions']
        return address_definitions
