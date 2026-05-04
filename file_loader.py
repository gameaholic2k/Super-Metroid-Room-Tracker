import json
import glob
from pathlib import Path
import configparser

class FileManager():
    def __init__(self):
        self.config = configparser.ConfigParser()
        self._config_file = 'config.ini'
        self.config.read(self.config_file)
        self.roomtime_config = self.config['roomtime_config']
        self._room_log_file = self.roomtime_config['room_log_file']
        self._run_category_directory = self.roomtime_config['category_folder']
        self._address_file = self.roomtime_config['address_file']
        self._room_log_directory = self.roomtime_config['room_log_file_folder']
        self._pre_defined_room_states_file = self.roomtime_config['pre_defined_room_states_file']
        self.channel_name = self.roomtime_config['channel_name']
        self.api_token = self.roomtime_config['api_token']

        # GUI config entries
        self.gui_config = self.config['gui_config']
        self.window_size = self.gui_config['window_size']
        self.min_horizontal_size = self.gui_config['min_horizontal_size']
        self.min_vertical_size = self.gui_config['min_vertical_size']
        self.default_run_category = self.get_default_run_category()

    @property
    def config_file(self):
        return self._config_file

    @property
    def room_log_file(self):
        return self._room_log_file
    
    @property
    def run_category_directory(self):
        return self._run_category_directory
    
    @property
    def address_file(self):
        return self._address_file
    
    @property
    def room_log_directory(self):
        return self._room_log_directory
    
    @property
    def pre_defined_room_states_file(self):
        return self._pre_defined_room_states_file

    def get_run_category_files(self):
        '''

        :return:
        '''
        json_files = glob.glob(f'{self.run_category_directory}/*.json')
        return json_files


    def get_default_run_category(self):
        default_category_config = self.roomtime_config['default_run_category']
        if not default_category_config:
            first_category = self.get_run_categories()[0]
            self.roomtime_config['default_run_category'] = first_category
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
