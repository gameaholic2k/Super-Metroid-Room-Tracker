import json
from typing import Final
import file_loader
import file_reader
import tkinter
from tkinter import ttk

from widgets import popup_window
from widgets.summary_display import SummaryFrame
from widgets.twitch_login import TwitchLogin
from widgets.options import Options
from websockets.sync.client import connect
import time
import threading
import traceback
import csv
from queue import Queue, Empty
import logging
import bisect
import statistics
from widgets.menu_bar import DropDownMenuBar
from widgets.notes import Notes
from widgets.delete_queue import DeleteQueue
from widgets.room_times_sheet import RoomTimesSheet
from widgets.room_times_history import RoomTimesHistory
from widgets.date_selection import DateSelection

logger = logging.getLogger(__name__)

class MainApplication:
    DEFAULT_COL: Final[int] = 0
    DEFAULT_ROW: Final[int] = 0
    def __init__(self, enable_extra_options: bool):
        self.queue: Queue[str] = Queue()
        self.stop_thread = threading.Event()
        self.thread = None
        self.sm_files = file_loader.FileManager()
        self.root = self._initialize_ttk_root()
        self.ttk_style = self._initialize_style()
        self.default_background_color: Final[str] = self.root.cget("bg")

        self.all_run_categories: Final[list[str]] = self.sm_files.get_run_categories()
        if not self.sm_files.roomtime_config['enabled_categories']:
            popup_window.initialize_category_popup_window(root=self.root,
                                                          run_category_names=self.all_run_categories,
                                                          config=self.sm_files.config,
                                                          config_file=self.sm_files.config_file)

        run_category_settings: dict[str, bool] = {}
        for category in self.all_run_categories:
            if category in self.sm_files.roomtime_config['enabled_categories'].split(","):
                run_category_settings[category] = True
            else:
                run_category_settings[category] = False
        enabled_categories = [key for key, value in run_category_settings.items() if value is True]
        self.log_handler = file_reader.RoomLogs(self.sm_files, enabled_categories)
        self.room_log_indexes_delete_queue: list[int] = []

        # Menu Bar
        self.menu_bar = DropDownMenuBar(self.root, self.sm_files.roomtime_config, run_category_settings)
        self.menu_bar.view_options_menu.entryconfigure(self.menu_bar.BACKGROUND_COLOR, command=self.on_background_color_menu_checkbox_selection)
        self.menu_bar.view_options_menu.entryconfigure(self.menu_bar.COLORED_SHEETS, command=self.on_color_sheet_menu_checkbox_selection)
        self.menu_bar.view_options_menu.entryconfigure(self.menu_bar.HIDE_EMPTY_ROWS, command=self.on_hide_rows_menu_checkbox_selection)
        self.menu_bar.view_options_menu.entryconfigure(self.menu_bar.HIDE_NOTES, command=self.on_hide_notes_menu_checkbox_selection)
        for category in self.all_run_categories:
            self.menu_bar.enabled_categories_menu.entryconfigure(category, command=lambda c=category: self.on_enable_category_menu_checkbox_selection(c))

        if enable_extra_options:
            self.menu_bar.menubar.add_cascade(label=self.menu_bar.EXTRA_OPTIONS, menu=self.menu_bar.extra_options_menu)
            self.menu_bar.extra_options_menu.entryconfigure(self.menu_bar.UPDATE_ITEM_COLLECTION_TIMES, command=self.update_item_collection_times)

        self.options = Options(self.sm_files.roomtime_config, parent_instance=self)
        # TOP Frame
        self.top_frame = ttk.Frame(self.root, padding=(12, 10))
        self.top_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        self.top_frame.columnconfigure(0, weight=0)
        self.top_frame.columnconfigure(1, weight=0)
        self.top_frame.columnconfigure(2, weight=0)
        self.top_frame.columnconfigure(3, weight=1)
        self.top_frame.rowconfigure(0, weight=0)

        self.summary_frame = SummaryFrame(self.top_frame)
        self.summary_frame.summary_frame.grid(row=0, column=0, sticky="w")

        # Main Mid-Frame
        self.mid_frame = ttk.Frame(self.root)
        self.mid_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        self.mid_frame.rowconfigure(0, weight=1)
        self.mid_frame.columnconfigure(0, weight=3, minsize=550)
        self.mid_frame.columnconfigure(1, weight=2)

        # Sub mid-sheet frame
        self.sub_mid_sheet_frame = ttk.Frame(self.mid_frame)
        self.sub_mid_sheet_frame.pack(fill=tkinter.BOTH, expand=True)

        self.room_time_sheet = RoomTimesSheet(self.sub_mid_sheet_frame)
        self.room_time_history = RoomTimesHistory(self.sub_mid_sheet_frame)
        self.room_time_history.add_delete_queue_button.config(command=self.add_to_delete_queue)
        self.room_time_sheet.sheet_frame.pack(side=tkinter.LEFT, fill=tkinter.BOTH, expand=True)
        self.room_time_history.room_history_frame.pack(side=tkinter.RIGHT, fill=tkinter.BOTH)

        self.date_selection = DateSelection(self.mid_frame, self.sm_files.roomtime_config)
        self.date_selection.date_selection_frame.pack(anchor=tkinter.W)
        self.date_selection.all_times_option.config(command=self.on_radio_date_selection)
        self.date_selection.daily_option.config(command=self.on_radio_date_selection)
        self.date_selection.weekly_option.config(command=self.on_radio_date_selection)
        self.date_selection.monthly_option.config(command=self.on_radio_date_selection)
        self.date_selection.last_num_of_days_option.config(command=self.on_radio_date_selection)
        self.date_selection.set_button.config(command=self.on_set_button_selection)


        # Right frame
        self.right_frame = ttk.Frame(self.root)
        self.right_frame.grid(row=0, column=1, rowspan=3, sticky="nsew", padx=10, pady=5)
        self.root.columnconfigure(0, weight=2, minsize=750)
        self.root.columnconfigure(1, weight=2)

        self.notes_widget = Notes(self.right_frame, self.sm_files.roomtime_config)
        self.notes_widget.edit_notes_checkbox.config(command=self.on_edit_notes_checkbox_selection)
        self.notes_widget.save_notes_button.config(command=self.on_save_notes_button_selection)

        if self.hide_notes_menu_checkbox is False:
            self.notes_widget.notes_frame.pack(fill=tkinter.BOTH, expand=True)

        self.delete_queue_widget = DeleteQueue(self.right_frame)
        self.delete_queue_widget.remove_queue_button.config(command=self.remove_from_delete_queue)
        self.delete_queue_widget.batch_delete_button.config(command=self.batch_delete)

        # BOTTOM Frame
        self.bottom_frame = ttk.Frame(self.root, padding=(8, 8))
        self.bottom_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(5, 5))
        self.bottom_frame.columnconfigure(1, weight=1)
        self.bottom_frame.columnconfigure(3, weight=1)

        self.twitch_login = TwitchLogin(self.bottom_frame, self.sm_files.roomtime_config)
        self.twitch_login.connect_button.config(command=self.on_button_click_connect)
        self.twitch_login.auto_connect_checkbox.config(command=self.on_auto_connect_checkbox_selection)
        self.twitch_login.twitch_login_frame.pack(side=tkinter.LEFT)

        self.sub_bottom_options_frame = ttk.Frame(self.bottom_frame)
        self.sub_frame_radio_buttons = ttk.Frame(self.sub_bottom_options_frame)

        self.option_rom_type_frame = self.options.initialize_rom_type_options(self.sub_frame_radio_buttons)
        self.option_rom_type_frame.pack(anchor=tkinter.NW)
        self.sub_frame_radio_buttons.pack(side=tkinter.LEFT)

        self.option_run_category_menu = self.options.initialize_run_category_menu_options(self.sub_bottom_options_frame,
                                                                                          self.log_handler.run_category_instances)
        self.option_run_category_menu.pack(side=tkinter.LEFT)

        self.sub_bottom_options_frame.pack(side=tkinter.LEFT)

        self.refresh_time_settings()

        current_font = self.table_sheet.font()
        bold_font = (current_font[0], current_font[1], 'bold')
        self.table_sheet.font(newfont=bold_font)
        self.color_background()
        self.color_sheets()

        self.previous_run_category_menu_selection = self.options.run_category_menu_selection.get()
        self.previous_rom_type_radio_button_selection = self.options.rom_type_radio_button_selection.get()

        #External bindings and trace
        self.table_sheet.extra_bindings('cell_select', self.on_sheet_select)
        self.table_sheet.extra_bindings('row_select', self.on_sheet_select)
        self.options.run_category_combo_box.bind('<<ComboboxSelected>>', self.on_run_category_menu_combobox_selection)

        # Auto connect if the auto connect option is checked
        if self.twitch_login.is_auto_connect.get() is True:
            self.twitch_login.connect_button.invoke()
        else:
            self.option_is_auto_connect_checkbox.config(state=tkinter.DISABLED)

        # Main loop to keep the GUI running
        self.root.mainloop()

    @property
    def is_practice_rom(self):
        return self.options.rom_type_radio_button_selection.get()

    @property
    def table_sheet(self):
        return self.room_time_sheet.sheet

    @table_sheet.setter
    def table_sheet(self, table):
        self.room_time_sheet.sheet.set_sheet_data(table)

    @property
    def listbox(self):
        return self.room_time_history.listbox

    @property
    def get_current_sheet_row_index_selection(self):
        if self.table_sheet.get_currently_selected():
            return self.table_sheet.data_r(self.table_sheet.get_currently_selected().row)
        else:
            return None

    @property
    def current_sheet_room_name(self):
        if self.table_sheet.get_currently_selected():
            selected_row = self.table_sheet.get_currently_selected().row
            return self.table_sheet.get_cell_data(selected_row, self.DEFAULT_COL)
        else:
            return None

    @property
    def selected_category_instance(self):
        return self.log_handler.run_category_instances[self.options.run_category_combo_box.get()]

    @property
    def time_units_selection(self):
        return self.date_selection.time_units_selection.get()

    #Funtoon reader properties
    @property
    def room_logs(self):
        if self.time_units_selection == self.date_selection.CURRENT_SESSION:
            return self.log_handler.get_current_session_logs(self.is_practice_rom)
        elif self.time_units_selection == self.date_selection.WEEKLY:
            return self.log_handler.get_weekly_logs(self.is_practice_rom)
        elif self.time_units_selection == self.date_selection.MONTHLY:
            return self.log_handler.get_monthly_logs(self.is_practice_rom)
        elif self.time_units_selection == self.date_selection.LAST_N_DAYS:
            if self.date_selection.num_of_days_entry.get().isdigit():
                return self.log_handler.get_days_ago_logs(self.is_practice_rom, int(self.date_selection.num_of_days_entry.get()))
            else:
                raise ValueError(f'Invalid number selected for number of days {self.date_selection.num_of_days_entry.get()}')
        else:
            if self.is_practice_rom:
                return self.log_handler.logs.practice_logs
            else:
                return self.log_handler.logs.vanilla_logs

    @room_logs.setter
    def room_logs(self, list_of_room_logs: list):
        if self.is_practice_rom:
            self.log_handler.logs.practice_logs = list_of_room_logs
        else:
            self.log_handler.logs.vanilla_logs = list_of_room_logs

    @property
    def all_room_logs(self):
        if self.is_practice_rom:
            return self.log_handler.logs.practice_logs
        else:
            return self.log_handler.logs.vanilla_logs

    @all_room_logs.setter
    def all_room_logs(self, list_of_room_logs: list):
        if self.is_practice_rom:
            self.log_handler.logs.practice_logs = list_of_room_logs
        else:
            self.log_handler.logs.vanilla_logs = list_of_room_logs

    @property
    def fastest_room_sessions(self):
        log_index_start =  len(self.all_room_logs) - len(self.room_logs)
        return self.selected_category_instance.get_fastest_room_times_table(self.all_room_logs, self.is_practice_rom, log_index_start)

    @property
    def personal_best_room_times(self):
        first_index_log = 0
        return self.selected_category_instance.get_fastest_room_times_table(self.all_room_logs, self.is_practice_rom,
                                                                            first_index_log)

    @property
    def average_room_times(self):
        log_index_start = len(self.all_room_logs) - len(self.room_logs)
        return self.selected_category_instance.get_average_room_times_table(self.all_room_logs, self.is_practice_rom, log_index_start)

    @property
    def run_category_indexes(self):
        if self.is_practice_rom:
            return self.selected_category_instance.run_category_indexes_practice
        else:
            return self.selected_category_instance.run_category_indexes_vanilla

    @run_category_indexes.setter
    def run_category_indexes(self, run_category_indexes: list):
        if self.is_practice_rom:
            self.selected_category_instance.run_category_indexes_practice = run_category_indexes
        else:
            self.selected_category_instance.run_category_indexes_vanilla = run_category_indexes


    # TODO use constants
    @property
    def room_log_time_key(self):
        if self.is_practice_rom:
            return 'practiceFrames'
        else:
            return 'frameCount'

    @property
    def room_log_file(self):
        if self.is_practice_rom:
            return self.sm_files.room_log_practice_file
        else:
            return self.sm_files.room_log_vanilla_file

    @property
    def delete_queue_listbox_widget(self):
        return self.delete_queue_listbox

    @property
    def delete_queue_frame(self):
        return self.delete_queue_widget.delete_queue_frame

    @property
    def notes_text_frame(self):
        return self.notes_widget.notes_frame

    @property
    def notes_text(self):
        return self.notes_widget.text_frame

    @property
    def edit_notes_checkbox(self):
        return self.notes_widget.edit_notes_checkbox

    @property
    def delete_queue_listbox(self):
        return self.delete_queue_widget.delete_queue_listbox

    @property
    def option_is_auto_connect_checkbox(self) -> ttk.Checkbutton:
        return self.twitch_login.auto_connect_checkbox

    @property
    def option_is_notes_editable(self) -> bool:
        return self.notes_widget.is_notes_editable.get()

    @property
    def option_hide_empty_rows(self) -> bool:
        return self.menu_bar.is_hide_empty_rows_menu_check.get()

    @property
    def option_is_background_color(self) -> bool:
        return self.menu_bar.is_background_color_menu_check.get()

    @property
    def option_is_colored_sheet(self) -> bool:
        return self.menu_bar.is_colored_sheet_menu_check.get()

    @property
    def hide_notes_menu_checkbox(self) -> bool:
        return self.menu_bar.is_hide_notes_menu_check.get()

    @property
    def time_units(self) -> str:
        return self.date_selection.time_units_selection.get()

    # GUI Interactions
    def on_sheet_select(self, event):
        self.refresh_times()

    def on_rom_type_radio_button_selection(self):
        if self.previous_rom_type_radio_button_selection != self.options.rom_type_radio_button_selection.get():
            self.refresh_all()
            self.previous_rom_type_radio_button_selection = self.options.rom_type_radio_button_selection.get()

    def on_background_color_menu_checkbox_selection(self):
        self.color_background()
        self.sm_files.update_roomtime_config('enable_colored_background', str(self.option_is_background_color))

    def on_color_sheet_menu_checkbox_selection(self):
        if self.option_is_colored_sheet is True:
            self.color_sheets()
        else:
            self.table_sheet.reset_all_options()
            self.table_sheet.redraw()
        self.sm_files.update_roomtime_config('colored_sheets', str(self.option_is_colored_sheet))

    def on_run_category_menu_combobox_selection(self, event):
        if self.previous_run_category_menu_selection != self.options.run_category_menu_selection.get():
            num_of_index_entries = self.selected_category_instance.get_number_of_index_entries_from_index_files(self.is_practice_rom)
            number_of_log_entries = len(self.all_room_logs)
            # Rebuilds the index if the number of index entries doesn't match up to the log entries
            if num_of_index_entries != number_of_log_entries:
                self.selected_category_instance.rebuild_run_category_index(self.is_practice_rom, self.log_handler.logs)
            self.refresh_all()
        self.sm_files.update_roomtime_config('default_run_category', self.selected_category_instance.category_name)

        self.color_sheets()
        self.previous_run_category_menu_selection = self.options.run_category_menu_selection.get()

    def on_edit_notes_checkbox_selection(self):
        if self.option_is_notes_editable is False:
            self.notes_text.configure(state=tkinter.DISABLED)
        else:
            self.notes_text.configure(state=tkinter.NORMAL)

    def on_save_notes_button_selection(self):
        if self.get_current_sheet_row_index_selection or self.get_current_sheet_row_index_selection == 0:
            text_notes = self.notes_text.get("1.0", "end-1c")

            if text_notes != "":
                self.selected_category_instance.user_room_data[self.get_current_sheet_row_index_selection]['notes'] = text_notes
                with open(self.selected_category_instance.get_run_category_user_data_filepath(), 'w') as file_handler:
                    json.dump(self.selected_category_instance.user_room_data, file_handler, indent=4)
                # Sets it back to read only after saving the notes
                if self.option_is_notes_editable is True:
                    self.edit_notes_checkbox.invoke()

    def on_add_to_delete_queue_button_selection(self):
        self.add_to_delete_queue()

    def on_hide_rows_menu_checkbox_selection(self):
        if self.menu_bar.is_hide_empty_rows_menu_check.get() is True:
            self.hide_empty_rows()
        else:
            self.table_sheet.display_rows('all', redraw=True)
        self.sm_files.update_roomtime_config('hide_empty_rows', str(self.menu_bar.is_hide_empty_rows_menu_check.get()))

    def on_hide_notes_menu_checkbox_selection(self):
        if self.hide_notes_menu_checkbox is True:
            self.notes_text_frame.pack_forget()
            if not self.delete_queue_frame.winfo_ismapped():
                self.right_frame.grid_forget()
        else:
            if self.delete_queue_frame.winfo_ismapped():
                self.delete_queue_frame.pack_forget()
                self.notes_text_frame.pack(fill=tkinter.BOTH, expand=True)
                self.delete_queue_frame.pack(fill=tkinter.BOTH, expand=True, pady=5)
            else:
                self.notes_text_frame.pack(fill=tkinter.BOTH, expand=True)
            if not self.right_frame.winfo_ismapped():
                self.right_frame.grid(row=0, column=1, rowspan=3, sticky="nsew", padx=10, pady=5)
        self.sm_files.update_roomtime_config('hide_notes', str(self.hide_notes_menu_checkbox))

    def on_button_click_connect(self):
        """
        Starts the websocket connection thread which is triggered from the connect button
        :return: None
        """
        if self.twitch_login.api_token_entry.get() and self.twitch_login.channel_entry.get():
            if self.thread is None or not self.thread.is_alive():
                self.stop_thread.clear()
                self.thread = threading.Thread(target=self.websocket_thread_function, daemon=True)
                self.thread.start()
                self.twitch_login.status_label.config(text="Status: Connecting...", style='Orange.TLabel')
                self.twitch_login.connect_button.config(state=tkinter.DISABLED)
                # Start checking the queue
                self.root.after(100, self.listen_for_result)
            else:
                self.stop_thread.set()
                self.twitch_login.status_label.config(text="Status: Disconnecting...", style='Red.TLabel')
                self.twitch_login.connect_button.config(state=tkinter.NORMAL)

    def on_auto_connect_checkbox_selection(self):
        self.sm_files.update_roomtime_config('auto_connect', str(self.twitch_login.is_auto_connect.get()))

    def on_enable_category_menu_checkbox_selection(self, menu_clicked: str):
        """
        Enables or disables a category.  Swaps to the first category if the current selected category is disabled.
        Do nothing when trying to deselect the last category.
        :param menu_clicked:
        :return:
        """
        if not any([var.get() for var in self.menu_bar.category_vars.values()]):
            self.menu_bar.category_vars[menu_clicked].set(True)
        else:
            enabled_categories = [key for key, var in self.menu_bar.category_vars.items() if var.get() is True]
            self.options.run_category_combo_box['values'] = enabled_categories
            if self.options.run_category_combo_box.get() not in self.options.run_category_combo_box['values']:
                first_option = 0
                self.options.run_category_combo_box.current(first_option)
                self.options.run_category_combo_box.event_generate("<<ComboboxSelected>>")
            if self.menu_bar.category_vars[menu_clicked].get() is True:
                self.log_handler.add_category_instance(menu_clicked)
            else:
                self.log_handler.run_category_instances.pop(menu_clicked, None)
            checked_categories = ','.join(enabled_categories)
            self.sm_files.update_roomtime_config('enabled_categories', checked_categories)

    def on_radio_date_selection(self):
        self.refresh_time_settings()

    def on_set_button_selection(self):
        num_of_days_entry = self.date_selection.num_of_days_entry.get()
        if num_of_days_entry.isdigit():
            self.sm_files.update_roomtime_config('num_of_days', str(num_of_days_entry))
            self.refresh_all()
        else:
            logger.info(f'Invalid number of days {num_of_days_entry}.')

    def _initialize_ttk_root(self):
        root = tkinter.Tk()
        root.title("Room Time Tracker")
        root.geometry(self.sm_files.window_size)
        root.minsize(int(self.sm_files.min_horizontal_size), int(self.sm_files.min_vertical_size))
        # # Main window grid config
        root.rowconfigure(1, weight=1)  # main content
        return root

    # Widget initialization
    def _initialize_style(self):
        ttk_style = ttk.Style()
        ttk_style.configure('Red.TLabel', foreground='red')
        ttk_style.configure('Orange.TLabel', foreground='orange')
        ttk_style.configure('Green.TLabel', foreground='green')
        ttk_style.configure('StatusTitle.TLabel', font=('TkDefaultFont', 10, 'bold'), foreground='black')
        ttk_style.configure("StatusValue.TLabel", font=('TkDefaultFont', 14, 'bold'))
        ttk_style.configure("PanelHeader.TLabel", font=('TkDefaultFont', 10, 'bold'))
        ttk_style.configure("PersonalBest.TLabel", foreground='green', font=('TkDefaultFont', 10, 'bold'))
        return ttk_style

    def color_background(self):
        if self.option_is_background_color is True:
            self.root.config(bg=self.sm_files.roomtime_config['background_color'])
        else:
            self.root.config(bg=self.default_background_color)

    def color_sheets(self):
        if self.option_is_colored_sheet is True:
            for index, room in enumerate(self.selected_category_instance.user_room_data):
                self.table_sheet.highlight_rows(rows=[index], bg=room['cell_color'], fg=room['text_color'])

    def refresh_time_settings(self):
        if self.time_units == self.date_selection.LAST_N_DAYS:
            self.date_selection.num_of_days_entry.config(state=tkinter.NORMAL)
            self.date_selection.set_button.config(state=tkinter.NORMAL)
        else:
            self.date_selection.num_of_days_entry.config(state=tkinter.DISABLED)
            self.date_selection.set_button.config(state=tkinter.DISABLED)

        self.refresh_all()

    def refresh_tables(self):
        self.table_sheet.set_sheet_data(self._get_table_sheet(), redraw=True)
        self.table_sheet.set_all_cell_sizes_to_text()

    def refresh_room_history(self):
        if not self.get_current_sheet_row_index_selection and self.get_current_sheet_row_index_selection != 0:
            self.table_sheet.select_cell(self.DEFAULT_ROW, self.DEFAULT_COL)

        # Clears the room history table before repopulating it
        self.listbox.delete(0, tkinter.END)

        log_index_start = len(self.all_room_logs) - len(self.room_logs)
        room_times = self.selected_category_instance.get_room_times_table_from_index_data(self.all_room_logs, self.is_practice_rom, log_index_start)
        room_times_history = room_times[self.get_current_sheet_row_index_selection]
        for frame_count in room_times_history:
            self.listbox.insert(tkinter.END, file_reader.convert_framecount_to_seconds(frame_count))


    def refresh_room_summary(self):

        if not self.get_current_sheet_row_index_selection and self.get_current_sheet_row_index_selection != 0:
            self.table_sheet.select_cell(self.DEFAULT_ROW, self.DEFAULT_COL)

        row_index = self.get_current_sheet_row_index_selection

        room_name = self.selected_category_instance.room_time_names[row_index]
        self.summary_frame.room_name_label.config(text=room_name)
        average_time = []

        if self.average_room_times:
            average_time = self.average_room_times[row_index]

        pb_time = []

        if self.personal_best_room_times:
            pb_time = self.personal_best_room_times[row_index]
        self.summary_frame.room_average_label.config(text=f"Average: {average_time if average_time else 'None'}")
        self.summary_frame.room_pb_label.config(text=f"PB: {pb_time if pb_time else 'None'}", style='StatusTitle.TLabel')

        log_index_start = len(self.all_room_logs) - len(self.room_logs)
        room_times = self.selected_category_instance.get_room_times_table_from_index_data(self.all_room_logs, self.is_practice_rom, log_index_start)
        if room_times:
            # if not room_times[row_index]:
            if row_index not in room_times:
                self.summary_frame.room_time_label.config(text="Current Room Time: None")
                return


    def refresh_room_notes(self):
        if self.get_current_sheet_row_index_selection or self.get_current_sheet_row_index_selection == 0:
            # Temporary sets the text widget to write mode even if the edit mode is unchecked
            if self.option_is_notes_editable is False:
                self.edit_notes_checkbox.invoke()
            self.notes_text.delete("1.0", tkinter.END)

            saved_notes = self.selected_category_instance.user_room_data[self.get_current_sheet_row_index_selection]['notes']
            self.notes_text.insert("1.0", saved_notes)
            # Sets notes back to read only after updating notes
            if self.option_is_notes_editable is True:
                self.edit_notes_checkbox.invoke()


    def update_item_collection_times(self):
        self.log_handler.update_item_collection_times()
        self.refresh_all()

    def append_room_time(self, room_log: dict):
        if 'VANILLA' in room_log['data']['gameTags']:
            self.options.rom_type_radio_button_selection.set(False)
        else:
            self.options.rom_type_radio_button_selection.set(True)

        logger.info(f'Writing to Log {self.sm_files.get_relative_path(self.room_log_file)}')
        self.log_handler.backup_logs()
        with open(self.room_log_file, 'a') as log_handler:
            log_handler.write(json.dumps(room_log) + '\n')
        logger.info(f'Finished appending to Log on row {len(self.all_room_logs)}')


        self.log_handler.update_room_logs(self.is_practice_rom)
        last_log_index = len(self.all_room_logs) - 1

        room_logic_index = self.selected_category_instance.get_run_category_room_logic_index(room_log_entry=room_log)

        if not room_logic_index and room_logic_index != 0:

            self.summary_frame.room_name_label.config(text=f'Undefined room transition')
            self.summary_frame.room_time_label.config(text="Room Time: None")
            self.summary_frame.room_average_label.config(text="Average: None")
            self.summary_frame.room_pb_label.config(text="PB: None", style='StatusTitle.TLabel')

            index_undefined_filepath = self.selected_category_instance.get_run_category_index_undefined_filepath(self.is_practice_rom)
            with open(index_undefined_filepath, 'r', newline='') as index_undefined_file:
                reader = csv.reader(index_undefined_file)

                indexes_undefined = next(reader)
            indexes_undefined.append(str(last_log_index))

            with open(index_undefined_filepath, 'w', newline='') as index_undefined_file:
                writer = csv.writer(index_undefined_file)
                writer.writerow(indexes_undefined)
            logger.info(
                f'Writing to {self.sm_files.get_relative_path(index_undefined_filepath)} with log index {last_log_index}')
            return None

        room_time_frames = room_log["data"][self.room_log_time_key]

        # Initializes the PB to false.  Set it to true if there's a PB or not a first time room entry
        room_time_pb = False
        if self.personal_best_room_times[room_logic_index]:
            fastest_room_time_frames = file_reader.convert_room_time_to_framecount(self.personal_best_room_times[room_logic_index])
            logger.info(f'{room_time_frames} < {fastest_room_time_frames}')
            if room_time_frames < fastest_room_time_frames:
                room_time_pb = True

        index_filepath = self.selected_category_instance.get_run_category_index_filepath(self.is_practice_rom)

        if self.run_category_indexes[room_logic_index]:
            # Fetches the room times to find where to insert the new time index
            room_times = [self.all_room_logs[int(index)]['data'][self.room_log_time_key] for index in self.run_category_indexes[room_logic_index]]
            index_to_insert = bisect.bisect_left(room_times, room_time_frames)

            bisect.insort(room_times, room_time_frames)
            self.run_category_indexes[room_logic_index].insert(index_to_insert, last_log_index)
        else:
            self.run_category_indexes[room_logic_index].append(last_log_index)

        logger.info(f'Writing to {self.sm_files.get_relative_path(index_filepath)} with logic index {room_logic_index} and log index {last_log_index}')
        with open(index_filepath, 'w', newline='') as csvfile_handler:
            csvwriter = csv.writer(csvfile_handler)
            csvwriter.writerows(self.run_category_indexes)

        if self.option_hide_empty_rows is True:
            self.hide_empty_rows()
            row_to_select = self.table_sheet.MT.displayed_rows.index(room_logic_index)
            # TODO Need a cleaner way to scroll down a bit more while hiding rows
            row_to_see = row_to_select

        else:
            row_to_select = room_logic_index
            if  row_to_select < self.table_sheet.total_rows() - 1:
                row_to_see = row_to_select + 1
            else:
                row_to_see = row_to_select

        self.table_sheet.select_cell(row_to_select, self.DEFAULT_COL)
        self.table_sheet.see(row_to_see, self.DEFAULT_COL)

        # Selects the room time history for new room entry
        room_time_in_seconds = file_reader.convert_framecount_to_seconds(room_time_frames)
        self.refresh_current_selected_row()
        first_listbox_index = 0
        updated_room_times = self.listbox.get(first_listbox_index, tkinter.END)
        if room_time_in_seconds in updated_room_times:
            matching_room_times = updated_room_times.index(room_time_in_seconds)
            self.listbox.selection_clear(first_listbox_index, tkinter.END)
            self.listbox.selection_set(matching_room_times)
            self.listbox.see(matching_room_times)


        self.summary_frame.room_time_label.config(text=f"Room Time: {room_time_in_seconds}")
        if room_time_pb:
            logger.info(f'PB: {room_time_in_seconds} *** NEW PB ***')
            self.summary_frame.room_pb_label.config(text=f'*NEW PB: {room_time_in_seconds}*', style='PersonalBest.TLabel')
        return None

    def _get_table_sheet(self):
        """

        :return:
        """
        table_sheet = []
        fastest = None
        average = None
        for index, room in enumerate(self.selected_category_instance.room_time_names):
            if self.fastest_room_sessions:
                fastest = self.fastest_room_sessions[index]
            if self.average_room_times:
                average = self.average_room_times[index]
            table_sheet.append([room, fastest, average])
        return table_sheet

    def refresh_current_selected_row(self):
        room_logic_index = self.get_current_sheet_row_index_selection
        logs_index_start = len(self.all_room_logs) - len(self.room_logs)
        print(f'logs_index_start: {logs_index_start}')
        room_times = [self.all_room_logs[int(index)]['data'][self.room_log_time_key]
                      for index in self.run_category_indexes[room_logic_index] if int(index) >= int(logs_index_start)]
        if not room_times:
            logging.exception(f'Failed to get current room times in room logic index: {room_logic_index} with index start: {logs_index_start}')
            logging.exception(f'run_category_indexes[{room_logic_index}]: {self.run_category_indexes[room_logic_index]}]')
            logging.exception(f'Length of all room logs: {len(self.all_room_logs)}')
            logging.exception(f'Length of selected room logs: {len(self.room_logs)}')
        fastest = file_reader.convert_framecount_to_seconds(min(room_times))
        average = file_reader.convert_framecount_to_seconds(round(statistics.mean(room_times)))
        self.fastest_room_sessions[room_logic_index] = fastest
        self.average_room_times[room_logic_index] = average
        fastest_col = 1
        average_col = 2

        self.table_sheet.set_cell_data(room_logic_index, fastest_col, fastest)
        self.table_sheet.set_cell_data(room_logic_index, average_col, average)
        self.table_sheet.redraw()


    def select_cell(self, event):
        self.refresh_room_history()
        self.refresh_room_summary()


    def hide_empty_rows(self):
        non_empty_rows = []
        for index, row in enumerate(self.fastest_room_sessions):
            if row or self.average_room_times[index]:
                non_empty_rows.append(index)
        self.table_sheet.display_rows(non_empty_rows, all_displayed=False, redraw=True)


    def get_log_indexes_from_room_history(self):
        log_index_start = len(self.all_room_logs) - len(self.room_logs)
        row_index_data = self.run_category_indexes[self.get_current_sheet_row_index_selection]
        row_index_data_filtered_time_unit = [int(log_index) for log_index in row_index_data if int(log_index) >= log_index_start]
        return row_index_data_filtered_time_unit

    def add_to_delete_queue(self):
        selected_indices = self.listbox.curselection()
        if not selected_indices:
            return

        if not self.get_current_sheet_row_index_selection and self.get_current_sheet_row_index_selection != 0:
            return

        # Fetches the index number of the log to delete based on the sheet row selection and room summary selection
        log_indexes_selected_row = self.get_log_indexes_from_room_history()
        for index in selected_indices:
            log_index = log_indexes_selected_row[index]
            room_name = self.current_sheet_room_name
            room_time = self.listbox.get(index)
            if log_index not in self.room_log_indexes_delete_queue:
                # Verifies if the room time matches with the log times
                room_time_from_log = file_reader.convert_framecount_to_seconds(
                    self.all_room_logs[log_index]['data'][self.room_log_time_key])
                if room_time_from_log != room_time:
                    logger.exception(f'Room time {room_time} does not match with time in logs {room_time_from_log}')
                    raise ValueError('Failed to add room time to the delete queue')

                queue_text = f'{room_name}: {room_time} -> Log Index: {log_index}'
                self.delete_queue_listbox_widget.insert(tkinter.END, queue_text)
                self.room_log_indexes_delete_queue.append(log_index)
                logger.info(f'Adding {log_index} to queue')

        if not self.delete_queue_frame.winfo_ismapped():
            self.delete_queue_frame.pack(fill=tkinter.BOTH, expand=True, pady=5)

        if not self.right_frame.winfo_ismapped():
            self.right_frame.grid(row=0, column=1, rowspan=3, sticky="nsew", padx=10, pady=5)


    def remove_from_delete_queue(self):
        selected_indices = self.delete_queue_listbox_widget.curselection()
        if not selected_indices:
            return
        selected_index = selected_indices[0]
        self.delete_queue_listbox_widget.delete(selected_index)
        log_index = self.room_log_indexes_delete_queue.pop(selected_index)
        logger.info(f'Removed {log_index} from queue')

        if not self.room_log_indexes_delete_queue:
            self.delete_queue_frame.pack_forget()

            if not self.notes_text.winfo_ismapped():
                self.right_frame.grid_forget()


    def batch_delete(self):
        if not self.room_log_indexes_delete_queue:
            return
        if len(self.room_log_indexes_delete_queue) != self.delete_queue_listbox_widget.size():
            logger.exception('Failed to batch delete.')
            logger.exception(f'Delete queue entries {self.room_log_indexes_delete_queue}')
            logger.exception(f'Delete listbox entries {self.delete_queue_listbox_widget}')
            raise RuntimeError(f'Delete queue contents does not match the displayed queue contents.')

        # Sort then sort in reverse order to avoid index shifting
        self.room_log_indexes_delete_queue.sort()
        for loop_index, log_index in enumerate(sorted(self.room_log_indexes_delete_queue, reverse=True)):
            room_info = self.delete_queue_listbox_widget.get(loop_index)
            logger.info(f'Deleting {room_info} room log entry on line {log_index}')

            # Tracking previous log length for delete verification
            previous_log_length = len(self.all_room_logs)
            del self.all_room_logs[log_index]
            new_log_length = len(self.all_room_logs)
            if previous_log_length == new_log_length:
                logger.exception(f'Failed to delete log index {log_index}')
                raise RuntimeError(f'Failed to delete log index {log_index}')

        logger.info(f'Writing to Log {self.sm_files.get_relative_path(self.room_log_file)}')
        self.log_handler.backup_logs()
        with open(self.room_log_file, 'w') as log_handler:
            for room in self.all_room_logs:
                log_handler.write(json.dumps(room) + '\n')

        logger.info(f'Successfully wrote changes to {self.sm_files.get_relative_path(self.room_log_file)}')

        # Clears the delete queue, queue display and performs a full rebuild
        self.room_log_indexes_delete_queue = []
        self.delete_queue_listbox_widget.delete(0, tkinter.END)
        self.delete_queue_frame.pack_forget()
        for category in self.log_handler.run_category_instances.values():
            category.rebuild_run_category_index(self.is_practice_rom, self.log_handler.logs)

        self.refresh_all()

        self.delete_queue_frame.pack_forget()

        if not self.notes_widget.notes_frame.winfo_ismapped():
            self.right_frame.grid_forget()


    def refresh_all(self):
        self.refresh_tables()
        self.refresh_room_history()
        self.refresh_room_summary()
        self.refresh_room_notes()

    def refresh_times(self):
        self.refresh_room_history()
        self.refresh_room_summary()
        self.refresh_room_notes()


    def websocket_thread_function(self):
        """

        :return:
        """
        try:

            channel = self.twitch_login.channel_entry.get()
            token = self.twitch_login.api_token_entry.get()
            with connect(f'wss://funtoon.party/tracking?channel={channel}&token={token}') as ws:
                self.queue.put('Authenticated.  Waiting for Funtoon to detect the next room transition.')
                logger.info('Connecting to funtoon')
                # Update config files

                if channel != self.sm_files.roomtime_config['channel_name'] or \
                        token != self.sm_files.roomtime_config['api_token']:
                    logger.info(f'Updating config file {self.sm_files.get_relative_path(self.sm_files.config_file)}')
                    self.sm_files.roomtime_config['channel_name'] = channel
                    self.sm_files.roomtime_config['api_token'] = token
                    with open(self.sm_files.config_file, 'w') as file_handler:
                        self.sm_files.config.write(file_handler)

                msg = ws.recv()
                if msg == '"invalid auth"':
                    self.queue.put('invalid auth')
                    logger.info('invalid auth')
                    return
                logger.info(f'Connected to funtoon as {channel}')
                self.queue.put(f'Connected to funtoon as {channel}')
                while not self.stop_thread.is_set():
                    msg = ws.recv()
                    msg_obj = json.loads(msg)
                    event = msg_obj['event']
                    print(event)
                    if event == 'smRoomTime':
                        self.queue.put(str(msg))

        except Exception as e:
            logger.exception(f"Error: {e}")
            traceback.print_exc()
        finally:
            self.queue.put("Disconnected")

    def listen_for_result(self):
        try:
            # Check for messages without blocking
            while True:
                msg = self.queue.get_nowait()
                if msg == 'Authenticated.  Waiting for Funtoon to detect the next room transition.':
                    self.twitch_login.status_label.config(text=msg, style='Orange.TLabel')
                    self.option_is_auto_connect_checkbox.config(state=tkinter.NORMAL)
                elif msg == f'Connected to funtoon as {self.twitch_login.channel_entry.get()}':
                    self.twitch_login.status_label.config(text=msg, style='Green.TLabel')
                    self.twitch_login.connect_button.config(state=tkinter.DISABLED)
                    self.option_is_auto_connect_checkbox.config(state=tkinter.NORMAL)
                elif msg == 'invalid auth':
                    self.twitch_login.status_label.config(text=f"invalid auth", style='Red.TLabel')
                    self.twitch_login.connect_button.config(state=tkinter.NORMAL)
                elif msg == 'Disconnected':
                    self.twitch_login.status_label.config(text=f"Disconnected", style='Red.TLabel')
                    self.twitch_login.connect_button.config(state=tkinter.NORMAL)

                if is_string_json(msg):
                    msg_data = json.loads(msg)
                    logger.info(f"Message Event {msg_data['event']}")
                    if msg_data['event'] == 'smRoomTime':
                        room_log = {'timestamp': time.time(), 'data': msg_data['data']}
                        self.append_room_time(room_log)
                # Schedule this function to run again after a delay (e.g., 100ms)
                self.root.after(100, self.listen_for_result)

        except Empty:
            pass
        self.root.after(100, self.listen_for_result)

def is_string_json(message) -> bool:
    try:
        json.loads(message)
        return True
    except ValueError:
        return False