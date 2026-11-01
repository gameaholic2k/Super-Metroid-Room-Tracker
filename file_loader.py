import json
import glob
import os
import logging
import shutil
from pathlib import Path
import configparser
from typing import Final

logger = logging.getLogger(__name__)

class FileManager:
    _DEFAULT_CATEGORY_KEY: Final[str] = 'default_run_category'
    _USER_DATA_FOLDER: Final[str] = 'user_data'
    _CONFIG_FILE_NAME: Final[str] = 'config.ini'


    def __init__(self) -> None:
        # User data directory
        self.script_dir: Final[Path] = Path(__file__).resolve().parent
        self.user_data_folder_path: Final[Path] = Path(os.path.join(self.script_dir, self._USER_DATA_FOLDER))
        self.config_file: Final[Path] = Path(os.path.join(self.script_dir, self._CONFIG_FILE_NAME))
        self.config = self.initialize_config()
        self.roomtime_config = self.config['roomtime_config']

        # User data subfolders
        self._user_data_subfolder_config = self.config['user_data_sub_folder']
        self.log_directory: Final[Path] = Path(os.path.join(self.user_data_folder_path, str(self._user_data_subfolder_config['log_folder'])))
        self.room_log_practice_file = Path(os.path.join(self.log_directory, self.roomtime_config['practice_room_log_file']))
        self.room_log_vanilla_file = Path(os.path.join(self.log_directory, self.roomtime_config['vanilla_room_log_file']))

        # Definition directory
        self.definition_path: Final[Path] = Path(os.path.join(self.script_dir, str(self.roomtime_config['definition_folder'])))
        self._address_file: Final[Path] = Path(os.path.join(self.definition_path, str(self.roomtime_config['address_file'])))
        self.pre_defined_room_states_file: Final[Path] = Path(os.path.join(self.definition_path, self.roomtime_config['pre_defined_room_states_file']))
        # Definition subfolders
        self.definition_subfolder_config = self.config['definition_sub_folder']
        self.run_category_directory: Final[Path] = Path(os.path.join(self.definition_path, self.definition_subfolder_config['category_folder']))

        # Index directory
        self.index_directory: Final[Path] = Path(os.path.join(self.user_data_folder_path, str(self._user_data_subfolder_config['index_folder'])))

        # Twitch
        self.channel_name: Final[str] = self.roomtime_config['channel_name']
        self.api_token: Final[str] = self.roomtime_config['api_token']

        # GUI
        self._gui_config = self.config['gui_config']
        self.window_size: Final[str] = self._gui_config['window_size']
        self.min_horizontal_size: Final[str] = self._gui_config['min_horizontal_size']
        self.min_vertical_size: Final[str] = self._gui_config['min_vertical_size']

        self.initialize_directories_and_files()


    def initialize_directories_and_files(self):
        self.index_directory.mkdir(parents=True, exist_ok=True)
        self.log_directory.mkdir(parents=True, exist_ok=True)

        if not self.roomtime_config['default_run_category']:
            self.set_default_run_category()

        # Split old roomtime file
        old_roomtime_file = Path(os.path.join(self.script_dir, 'list_of_roomtimes.jsonl'))
        if old_roomtime_file.exists():
            logger.info(f'Importing logs from {self.get_relative_path(old_roomtime_file)}')

            practice_data = []
            vanilla_data = []
            with open(old_roomtime_file, 'r') as log_handler:
                for line in log_handler:
                    line_room_data = json.loads(line)
                    if 'VANILLA' in line_room_data['data']['gameTags'] and int(line_room_data['data']['frameCount']) >= 0:
                        vanilla_data.append(line_room_data)
                    if 'PRACTICE' in line_room_data['data']['gameTags']:
                        if int(line_room_data['data']['practiceFrames']) >= 0:
                            practice_data.append(line_room_data)
            self.room_log_practice_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.room_log_practice_file, 'w') as practice_log_handler:
                for room_data in practice_data:
                    # Serialize the dictionary to a JSON string and append a newline
                    practice_log_handler.write(json.dumps(room_data) + "\n")

            self.room_log_vanilla_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.room_log_vanilla_file, 'w') as vanilla_log_handler:
                for room_data in vanilla_data:
                    # Serialize the dictionary to a JSON string and append a newline
                    vanilla_log_handler.write(json.dumps(room_data) + "\n")
            backup = Path(os.path.join(self.script_dir, 'list_of_roomtimes.jsonl.bak'))
            shutil.copy2(old_roomtime_file, backup)
            logger.info(f"Backed up 'list_of_roomtimes.jsonl' to 'list_of_roomtimes.jsonl.bak'")
            old_roomtime_file.unlink(missing_ok=True)


    def initialize_config(self):
        config = configparser.ConfigParser()

        # move_old_files(self._CONFIG_FILE_NAME, self.user_data_folder_path)
        if not self.config_file.exists():
            # Create the config directory if it doesn't exist
            print(f"{self.config_file} doesn't exist")
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            self.config_file.touch()

        config.read(self.config_file)
        room_time_config_key = 'roomtime_config'

        config_setting(config, room_time_config_key, 'channel_name', '')
        config_setting(config, room_time_config_key, 'api_token',  '')
        config_setting(config, room_time_config_key, 'auto_connect', 'False')
        config_setting(config, room_time_config_key, 'default_run_category', '')
        config_setting(config, room_time_config_key, 'enabled_categories', '')
        config_setting(config, room_time_config_key, 'colored_sheets', 'True')
        config_setting(config, room_time_config_key, 'enable_colored_background', 'True')
        config_setting(config, room_time_config_key, 'background_color', '#018281')
        config_setting(config, room_time_config_key, 'hide_empty_rows', 'False')
        config_setting(config, room_time_config_key, 'hide_notes', 'False')
        config_setting(config, room_time_config_key, 'time_units', 'All Times')
        config_setting(config, room_time_config_key, 'num_of_days', '7')

        config_setting(config, room_time_config_key, 'definition_folder', 'definition')
        definition_sub_folder_key = 'definition_sub_folder'
        config_setting(config, definition_sub_folder_key, 'category_folder', 'categories')
        config_setting(config, room_time_config_key, 'address_file', 'SuperMetroid.json')
        config_setting(config, room_time_config_key, 'pre_defined_room_states_file', 'pre_defined_room_states.json')

        user_data_sub_folder_key = 'user_data_sub_folder'
        config_setting(config, user_data_sub_folder_key, 'log_folder', 'logs')
        config_setting(config, user_data_sub_folder_key, 'index_folder', 'indexes')
        config_setting(config, room_time_config_key, 'practice_room_log_file', 'list_of_roomtimes_practice.jsonl')
        config_setting(config, room_time_config_key, 'vanilla_room_log_file', 'list_of_roomtimes_vanilla.jsonl')

        gui_config_key = 'gui_config'
        config_setting(config, gui_config_key, 'window_size', '1100x900')
        config_setting(config, gui_config_key, 'min_horizontal_size', '820')
        config_setting(config, gui_config_key, 'min_vertical_size', '760')

        with open(self.config_file, 'w') as config_file:
            config.write(config_file)
        return config



    def update_roomtime_config(self, config_key: str, config_value: str):
        with open(self.config_file, 'w') as file_handler:
            previous_value = self.roomtime_config[config_key]
            logger.info(f'Editing config key {config_key}: {previous_value} -> {config_value}.  '
                        f'writing to {self.get_relative_path(self.config_file)}')
            self.roomtime_config[config_key] = config_value
            self.config.write(file_handler)

    def get_run_category_files(self):
        """

        :return:
        """
        json_files = glob.glob(f'{self.run_category_directory}/*.json')
        return json_files

    def set_default_run_category(self):
        default_category_config = self.roomtime_config[self._DEFAULT_CATEGORY_KEY]
        if not default_category_config:
            first_category = self.get_run_categories()[0]
            self.roomtime_config[self._DEFAULT_CATEGORY_KEY] = first_category
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
    
    def get_room_logs(self, is_practice_rom: bool):
        """

        :return:
        """
        data = []
        if is_practice_rom:
            room_log_file = self.room_log_practice_file
        else:
            room_log_file = self.room_log_vanilla_file

        if not Path(room_log_file).exists():
            with open(room_log_file, 'w'):
                pass
        with open(room_log_file, 'r') as f:
            for line in f:
                data.append(json.loads(line))
        return data

    def get_address_definitions(self) -> dict:
        """

        :return:
        """
        with open(self._address_file, 'r') as f:
            address_definitions = json.load(f)['definitions']
        return address_definitions

    def get_relative_path(self, file_path: Path) -> Path:
        return file_path.relative_to(self.script_dir)


def config_setting(config, section, key, default_value):
    if not config.has_section(section):
        config.add_section(section)
    if not config.has_option(section, key):
        config.set(section, key, default_value)

