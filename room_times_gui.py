import json
from dataclasses import dataclass
import read_funtoon_data
import tkinter
from tkinter import ttk
from tksheet import Sheet
from websockets.sync.client import connect
import time
import threading
import traceback
import csv
from queue import Queue, Empty

@dataclass
class FrameData:
    index: int
    frame_count: str


class RoomTimeTrackerGUI:
    def __init__(self):
        self.sm = read_funtoon_data.SuperMetroidRooms()
        #TODO select last saved category from config file
        # self.selected_category = self.sm.run_categories[0]
        self.selected_category = self.sm.run_categories[self.sm.sm_files.default_run_category]
        self.fastest_room_times = self.sm.get_fastest_room_times(self.selected_category)
        self.average_room_times = self.sm.get_average_room_times(self.selected_category)

        #TODO create another class for storing widgets
        # TK Root
        self.root = tkinter.Tk()
        self.root.title("Room Time Tracker")
        self.root.geometry(self.sm.sm_files.window_size)
        self.root.minsize(int(self.sm.sm_files.min_horizontal_size), int(self.sm.sm_files.min_vertical_size))

        # Thread-safe queue for communication
        self.queue = Queue()
        self.stop_thread = threading.Event()
        self.thread = None

        # Tk variables
        self.hide_empty_rows_var = tkinter.BooleanVar(value=False)
        self.run_category_radio_button_selection = tkinter.StringVar(value=self.selected_category.run_category)

        # Selection / row-mapping state
        self.visible_row_to_actual_row = []
        self.actual_row_to_visible_row = {}
        self.current_selected_actual_row = None

        # Display-order mapping for the currently selected room's listbox entries.
        # Keep this separate from the underlying chronology/index order.
        self.current_display_log_indexes = []

        #Styles
        self.ttk_style = ttk.Style()
        self.ttk_style.configure('Red.TLabel', foreground='red')
        self.ttk_style.configure('Orange.TLabel', foreground='orange')
        self.ttk_style.configure('Green.TLabel', foreground='green')
        self.ttk_style.configure('StatusTitle.TLabel', font=('TkDefaultFont', 10, 'bold'))
        self.ttk_style.configure("StatusValue.TLabel", font=('TkDefaultFont', 14, 'bold'))
        self.ttk_style.configure("PanelHeader.TLabel", font=('TkDefaultFont', 10, 'bold'))

        # Main window grid config
        self.root.rowconfigure(0, weight=0)  # top status banner
        self.root.rowconfigure(1, weight=1)  # main content
        self.root.rowconfigure(2, weight=0)  # bottom utility bar
        self.root.columnconfigure(0, weight=1)

        # Frames
        self.status_frame = ttk.Frame(self.root, padding=(12, 10))
        self.status_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))

        self.main_frame = ttk.Frame(self.root)
        self.main_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)

        self.utility_frame = ttk.Frame(self.root, padding=(8, 8))
        self.utility_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(5, 0))

        # Main content grid
        self.main_frame.rowconfigure(0, weight=1)
        self.main_frame.columnconfigure(0, weight=3)
        self.main_frame.columnconfigure(1, weight=2)

        self.table_frame = ttk.Frame(self.main_frame)
        self.table_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        self.detail_frame = ttk.Frame(self.main_frame)
        self.detail_frame.grid(row=0, column=1, sticky="nsew")

        self.table_frame.rowconfigure(0, weight=1)
        self.table_frame.rowconfigure(1, weight=0)
        self.table_frame.columnconfigure(0, weight=1)

        self.detail_frame.rowconfigure(1, weight=1)
        self.detail_frame.columnconfigure(0, weight=1)

        # Status banner layout
        self.status_frame.columnconfigure(0, weight=0)
        self.status_frame.columnconfigure(1, weight=0)
        self.status_frame.columnconfigure(2, weight=0)
        self.status_frame.columnconfigure(3, weight=1)

        self.room_name_label = ttk.Label(
            self.status_frame,
            text="None",
            style="StatusValue.TLabel",
            font=("TkDefaultFont", 16, "bold")
        )
        self.room_name_label.grid(row=0, column=0, columnspan=2, sticky="w")

        self.room_time_label = ttk.Label(
            self.status_frame,
            text="Room Time: None",
            style="StatusTitle.TLabel"
        )
        self.room_time_label.grid(row=1, column=0, sticky="w", pady=(4, 0))

        self.room_average_label = ttk.Label(
            self.status_frame,
            text="Average: None",
            style="StatusTitle.TLabel"
        )
        self.room_average_label.grid(row=1, column=1, sticky="w", padx=(20, 0), pady=(4, 0))

        self.room_pb_label = ttk.Label(
            self.status_frame,
            text="PB: None",
            style="StatusTitle.TLabel"
        )
        self.room_pb_label.grid(row=1, column=2, sticky="w", padx=(20, 0), pady=(4, 0))

        # Left: summary table
        self.table_sheet = self._get_table_sheet()

        self.sheet = Sheet(self.table_frame)
        self.sheet.grid(row=0, column=0, sticky="nsew")
        self.sheet.headers(["Room Name", "Fastest Time", "Average Time"])
        self.sheet.set_sheet_data(self.table_sheet)
        self.sheet.set_all_cell_sizes_to_text()
        self.sheet.enable_bindings((
            "single_select",
            "row_select",
            "column_select",
            "select_rows",
            "drag_select",
            "copy",
            "arrowkeys",
        ))
        self._bind_sheet_selection_events()

        self.hide_empty_checkbox = ttk.Checkbutton(
            self.table_frame,
            text="Hide empty rows",
            variable=self.hide_empty_rows_var,
            command=self.refresh_tables
        )
        self.hide_empty_checkbox.grid(row=1, column=0, sticky="w", pady=(8, 0))

        # Right: detail panel
        self.detail_header = ttk.Label(
            self.detail_frame,
            text="Selected Room History",
            style="PanelHeader.TLabel"
        )
        self.detail_header.grid(row=0, column=0, sticky="w", pady=(0, 8))

        self.listbox = tkinter.Listbox(self.detail_frame, selectmode=tkinter.SINGLE)
        self.listbox.grid(row=1, column=0, sticky="nsew")

        self.scrollbar = ttk.Scrollbar(
            self.detail_frame,
            orient=tkinter.VERTICAL,
            command=self.listbox.yview
        )
        self.scrollbar.grid(row=1, column=1, sticky="ns")
        self.listbox.config(yscrollcommand=self.scrollbar.set)

        self.select_button = ttk.Button(
            self.detail_frame,
            text="Delete Selected Room Time",
            command=self.delete_entry
        )
        self.select_button.grid(row=2, column=0, sticky="ew", pady=(8, 4))

        # Run category radios
        self.category_frame = ttk.Frame(self.detail_frame)
        self.category_frame.grid(row=3, column=0, sticky="w", pady=(8, 0))
        for row, category in enumerate(self.sm.run_categories.values()):
            ttk.Radiobutton(
                self.category_frame,
                text=category.run_category,
                variable=self.run_category_radio_button_selection,
                value=category.run_category,
                command=self.change_category
            ).grid(row=row, column=0, sticky="w")

        # Bottom utility bar
        self.utility_frame.columnconfigure(1, weight=1)
        self.utility_frame.columnconfigure(3, weight=1)

        self.channel_label = ttk.Label(self.utility_frame, text="Twitch Channel Name:")
        self.channel_label.grid(row=0, column=0, padx=(0, 5), pady=2, sticky="w")

        self.channel_entry = ttk.Entry(self.utility_frame)
        self.channel_entry.grid(row=0, column=1, padx=(0, 12), pady=2, sticky="ew")
        self.channel_entry.insert(0, self.sm.sm_files.channel_name)

        self.api_token_label = ttk.Label(self.utility_frame, text="FUNtoon API Token:")
        self.api_token_label.grid(row=0, column=2, padx=(0, 5), pady=2, sticky="w")

        self.api_token_entry = ttk.Entry(self.utility_frame, show="*")
        self.api_token_entry.grid(row=0, column=3, padx=(0, 12), pady=2, sticky="ew")
        self.api_token_entry.insert(0, self.sm.sm_files.api_token)

        self.connect_button = ttk.Button(
            self.utility_frame,
            text="Connect",
            command=self.on_button_click_connect
        )
        self.connect_button.grid(row=0, column=4, padx=(0, 12), pady=2, sticky="w")

        status_sample_text = "Status: Authenticated, waiting for next transition"
        self.status_label = ttk.Label(
            self.utility_frame,
            text="Status: Disconnected",
            style="Red.TLabel",
            anchor="w",
            width=len(status_sample_text)
        )
        self.status_label.grid(row=0, column=5, sticky="w", pady=2)

        self.channel_entry.focus()

        if self.visible_row_to_actual_row:
            self.root.after(50, lambda: self.select_room_by_actual_index(self.visible_row_to_actual_row[0]))

        self.root.mainloop()

    def _bind_sheet_selection_events(self):
        for event_name in (
            "<ButtonRelease-1>",
            "<KeyRelease-Up>",
            "<KeyRelease-Down>",
            "<KeyRelease-Left>",
            "<KeyRelease-Right>",
            "<<TreeviewSelect>>",
        ):
            try:
                self.sheet.bind(event_name, self.on_sheet_selection_event)
            except Exception:
                pass

        try:
            self.sheet.extra_bindings("cell_select", self.on_sheet_selection_event)
        except Exception:
            pass

        try:
            self.sheet.extra_bindings("row_select", self.on_sheet_selection_event)
        except Exception:
            pass

        try:
            self.sheet.extra_bindings("select", self.on_sheet_selection_event)
        except Exception:
            pass

    def on_sheet_selection_event(self, event=None):
        self.root.after(1, self.sync_right_panel_from_sheet_selection)

    def sync_right_panel_from_sheet_selection(self):
        visible_row = self.get_selected_sheet_visible_row()
        if visible_row is None:
            return

        actual_row = self.visible_row_to_actual_row_from_visible(visible_row)
        if actual_row is None:
            return

        self.populate_room_log_list(actual_row)

    def get_selected_sheet_visible_row(self):
        getter_names = [
            "get_currently_selected",
            "currently_selected",
            "get_selected_cells",
            "get_selected_rows",
        ]

        for name in getter_names:
            if hasattr(self.sheet, name):
                try:
                    value = getattr(self.sheet, name)()

                    if name == "get_selected_rows" and value:
                        if isinstance(value, (list, tuple)):
                            first = value[0]
                            if isinstance(first, int):
                                return first

                    if isinstance(value, tuple):
                        if len(value) >= 1 and isinstance(value[0], int):
                            return value[0]

                    if hasattr(value, "row"):
                        row = getattr(value, "row")
                        if isinstance(row, int):
                            return row

                    if isinstance(value, dict):
                        row = value.get("row")
                        if isinstance(row, int):
                            return row

                    if isinstance(value, (list, tuple)) and value:
                        first = value[0]
                        if isinstance(first, tuple) and len(first) >= 1 and isinstance(first[0], int):
                            return first[0]
                except Exception:
                    pass

        return None

    def visible_row_to_actual_row_from_visible(self, visible_row):
        if visible_row is None:
            return None
        if visible_row < 0 or visible_row >= len(self.visible_row_to_actual_row):
            return None
        return self.visible_row_to_actual_row[visible_row]

        # # Create a top frame
        # self.top_frame = tkinter.Frame(self.root)
        # self.top_frame.pack(side=tkinter.TOP, fill=tkinter.BOTH, expand=True, padx=10, pady=5)
        #
        # # Create a right frame
        # self.right_frame = tkinter.Frame(self.root)
        # self.right_frame.pack(side=tkinter.RIGHT, fill=tkinter.BOTH, expand=True, padx=10, pady=5)
        #
        # # Create a bottom frame
        # self.bottom_frame = tkinter.Frame(self.root)
        # self.bottom_frame.pack(side=tkinter.BOTTOM, fill=tkinter.BOTH, expand=True, padx=10, pady=5)

        # # Channel label
        # self.channel_label = ttk.Label(self.top_frame, text="Twitch Channel Name:")
        # self.channel_label.grid(row=0, column=0, padx=5, pady=5)
        #
        # # Channel Entry Widget
        # # The key is the 'show="*" ' option
        # self.channel_entry = ttk.Entry(self.top_frame)
        # self.channel_entry.grid(row=1, column=0, padx=5, pady=5)
        # self.channel_entry.focus() # Set focus to the entry box initially
        # self.channel_entry.insert(0, self.sm.sm_files.channel_name)
        #
        # # API Token label
        # self.api_token_label = ttk.Label(self.top_frame, text="FUNtoon API Token:")
        # self.api_token_label.grid(row=0, column=1, padx=5, pady=5)
        #
        # # API Entry Widget
        # # The key is the 'show="*" ' option
        # self.api_token_entry = ttk.Entry(self.top_frame, show="*")
        # self.api_token_entry.grid(row=1, column=1, padx=5, pady=5)
        # self.api_token_entry.focus() # Set focus to the entry box initially
        # self.api_token_entry.insert(0, self.sm.sm_files.api_token)
        #
        # self.connect_button = ttk.Button(self.top_frame, text="Connect", command=self.on_button_click_connect)
        # self.connect_button.grid(row=0, column=2, padx=5, pady=5)
        #
        # # Spreadsheet for times
        # self.sheet = Sheet(self.bottom_frame, height=500, width=700)
        # self.sheet.grid(row=0, column=0, padx=5, pady=5)




        # self.sheet.headers(["Room name", "Fastest Time", "Average Time"])
        # self.sheet.set_sheet_data(self.table_sheet)
        # self.sheet.set_all_cell_sizes_to_text()
        # self.sheet.enable_bindings((
        #     "single_select",  # Allow selecting single cells
        #     "row_select",     # Allow selecting full rows
        #     "column_select",  # Allow selecting full columns
        #     "select_rows",    # Enable row selection
        #     "drag_select",    # Enable drag selection
        #     "copy",           # Enable copy spreadsheet
        # ))
        #
        # # Listbox for roomtimes
        # self.listbox = tkinter.Listbox(self.right_frame, selectmode=tkinter.SINGLE) # height sets the number of lines visible
        # self.listbox.grid(row=1, column=0, padx=5, pady=5)
        #
        # # Attach a scrollbar (optional, but recommended for long lists)
        # self.scrollbar = ttk.Scrollbar(self.root, orient=tkinter.VERTICAL, command=self.listbox.yview)
        # self.scrollbar.pack(side=tkinter.RIGHT, fill=tkinter.Y)
        # self.listbox.config(yscrollcommand=self.scrollbar.set)
        #
        # # Add a button to show the selected value
        # self.select_button = ttk.Button(self.right_frame, text="Delete selected room log", command=self.delete_entry)
        # self.select_button.grid(row=3, column=0, padx=5, pady=5)
        #
        # # Add a label to display the selection result
        # self.selection_label = ttk.Label(self.right_frame, text="Selected: None")
        # self.selection_label.grid(row=4, column=0, padx=5, pady=5)
        #
        # # Drop down menu for rooms
        # self.room_dropdown_menu = ttk.Combobox(self.right_frame, state='readonly')
        # self.room_dropdown_menu.grid(row=0, column=0, padx=5, pady=5)
        # self.room_dropdown_menu.bind("<<ComboboxSelected>>", self.dropdown_menu_select)
        # self.update_drop_down_menu()
        #
        #
        #
        # self.status_label = ttk.Label(self.root, text="Status: Disconnected", style='Red.TLabel')
        # self.status_label.pack()
        #
        # # Initialize the shared Tkinter variable for run category index
        #
        # for row, category in enumerate(self.sm.run_categories.values()):
        #     ttk.Radiobutton(self.right_frame, text=category.run_category, variable=self.run_category_radio_button_selection, value=category.run_category, command=self.change_category).grid(row=row+5, column=0, sticky="W")


    def change_category(self):
        radio_button_selection = self.run_category_radio_button_selection.get()
        self.selected_category = self.sm.run_categories[radio_button_selection]
        self.sm.rebuild_run_category_index(self.selected_category)

        previous_selected_actual_row = self.current_selected_actual_row
        self.refresh_tables()

        if previous_selected_actual_row is not None:
            self.root.after(1, lambda: self.select_room_by_actual_index(previous_selected_actual_row))
        elif self.visible_row_to_actual_row:
            self.root.after(1, lambda: self.select_room_by_actual_index(self.visible_row_to_actual_row[0]))

        self.sm.sm_files.roomtime_config['default_run_category'] = radio_button_selection
        with open(self.sm.sm_files.config_file, 'w') as file_handler:
            self.sm.sm_files.config.write(file_handler)

    def on_button_click_connect(self):
        '''
        Starts the websocket connection thread which is triggered from the connect button
        :return: None
        '''
        if self.api_token_entry.get() and self.channel_entry.get():
            if self.thread is None or not self.thread.is_alive():
                self.stop_thread.clear()
                self.thread = threading.Thread(target=self.websocket_thread_function, daemon=True)
                self.thread.start()
                self.status_label.config(text="Status: Connecting...", style='Orange.TLabel')
                self.connect_button.config(state=tkinter.DISABLED)
                # Start checking the queue
                self.root.after(100, self.listen_for_result)
            else:
                self.stop_thread.set()
                self.status_label.config(text="Status: Disconnecting...", style='Red.TLabel')
                self.connect_button.config(state=tkinter.NORMAL)

    def listen_for_result(self):
        try:
            # Check for messages without blocking
            while True:
                msg = self.queue.get_nowait()

                print(f'Message type {type(msg)}')
                print(msg)
                if msg == 'Authenticated.  Waiting for Funtoon to detect the next room transition.':
                    self.status_label.config(text=msg, style='Orange.TLabel')
                elif msg == f'Connected to funtoon as {self.channel_entry.get()}':
                    self.status_label.config(text=msg, style='Green.TLabel')
                    self.connect_button.config(state=tkinter.DISABLED)
                    # return  # Stop checking
                elif msg == 'invalid auth':
                    self.status_label.config(text=f"invalid auth", style='Red.TLabel')
                    self.connect_button.config(state=tkinter.NORMAL)
                    # return  # Stop checking
                elif msg == 'Disconnected':
                    self.status_label.config(text=f"Disconnected", style='Red.TLabel')
                    self.connect_button.config(state=tkinter.NORMAL)
                    # return  # Stop checking

                elif msg == 'test':
                        print('queue test')

                if isinstance(msg, dict):
                    print(f"Message Event {msg['event']}")
                    if msg['event'] == 'smRoomTime':
                        room_log = {'timestamp': time.time(),
                                     'data': msg['data']}
                        self.append_room_time(room_log)
                # Schedule this function to run again after a delay (e.g., 100ms)
                self.root.after(100, self.listen_for_result)

        except Empty:
            pass
        self.root.after(100, self.listen_for_result)

    def _get_table_sheet(self):
        '''

        :param room_time_names:
        :param fastest_room_times:
        :param average_room_times:
        :return:
        '''
        table_sheet = []
        self.visible_row_to_actual_row = []
        self.actual_row_to_visible_row = {}

        visible_row = 0
        print(f'Room Time length: {len(self.selected_category.room_time_names)}')
        print(f'Fastest Room Time length: {len(self.fastest_room_times)}')
        print(f'Average Room Time length: {len(self.average_room_times)}')
        for index, room in enumerate(self.selected_category.room_time_names):
            fastest = self.fastest_room_times[index]
            average = self.average_room_times[index]

            if self.hide_empty_rows_var.get() and not fastest and not average:
                continue

            table_sheet.append([room, fastest, average])
            self.visible_row_to_actual_row.append(index)
            self.actual_row_to_visible_row[index] = visible_row
            visible_row += 1

        return table_sheet

    def populate_room_log_list(self, actual_row_index):
        self.listbox.delete(0, tkinter.END)
        self.current_selected_actual_row = actual_row_index
        self.current_display_log_indexes = []

        room_times = self.sm.get_room_times_from_index(self.selected_category)

        print(f"length of roomtimes {len(room_times)}")
        print(f"{self.selected_category.run_category} actual index: {actual_row_index} from sheet selection")

        if actual_row_index < 0 or actual_row_index >= len(room_times):
            self.room_name_label.config(text="None")
            self.room_time_label.config(text="Room Time: None")
            self.room_average_label.config(text="Average: None")
            self.room_pb_label.config(text="PB: None")
            return

        room_name = self.selected_category.room_time_names[actual_row_index]
        self.room_name_label.config(text=room_name)
        average_time = self.average_room_times[actual_row_index]
        pb_time = self.fastest_room_times[actual_row_index]
        self.room_average_label.config(text=f"Average: {average_time if average_time else 'None'}")
        self.room_pb_label.config(text=f"PB: {pb_time if pb_time else 'None'}")

        if not room_times[actual_row_index]:
            self.room_time_label.config(text="Room Time: None")
            return

        print(room_times[actual_row_index])
        print(self.selected_category.run_category_indexes[actual_row_index])

        display_pairs = sorted(
            zip(
                room_times[actual_row_index],
                self.selected_category.run_category_indexes[actual_row_index]
            )
        )

        display_room_times = [pair[0] for pair in display_pairs]
        self.current_display_log_indexes = [str(pair[1]) for pair in display_pairs]

        for room_time in display_room_times:
            self.listbox.insert(
                tkinter.END,
                read_funtoon_data.convert_framecount_to_seconds(room_time)
            )

        latest_log_index = max(int(i) for i in self.selected_category.run_category_indexes[actual_row_index])
        latest_time = read_funtoon_data.convert_framecount_to_seconds(
            self.sm.room_logs[latest_log_index]["data"]["practiceFrames"]
        )
        self.room_time_label.config(text=f"Room Time: {latest_time}")

    def select_room_by_actual_index(self, actual_row_index, refresh_right_panel=True):
        if actual_row_index not in self.actual_row_to_visible_row:
            if refresh_right_panel:
                self.current_selected_actual_row = None
                self.current_display_log_indexes = []
                self.listbox.delete(0, tkinter.END)
                self.room_name_label.config(text="None")
                self.room_time_label.config(text="Room Time: None")
                self.room_average_label.config(text="Average: None")
                self.room_pb_label.config(text="PB: None")
            return

        visible_row = self.actual_row_to_visible_row[actual_row_index]

        try:
            if hasattr(self.sheet, "set_currently_selected"):
                self.sheet.set_currently_selected(visible_row, 0)
        except Exception:
            pass

        try:
            if hasattr(self.sheet, "select_row"):
                self.sheet.select_row(visible_row)
        except Exception:
            pass

        try:
            if hasattr(self.sheet, "see"):
                self.sheet.see(visible_row, 0)
        except Exception:
            pass

        try:
            if hasattr(self.sheet, "redraw"):
                self.sheet.redraw()
        except Exception:
            pass

        if refresh_right_panel:
            self.populate_room_log_list(actual_row_index)

    def delete_entry(self):
        '''
        Deletes the room time entry.  Index needs to be rebuilt after every entry is deleted
        :return: None
        '''
        selected_indices = self.listbox.curselection()
        if not selected_indices:
            return

        if self.current_selected_actual_row is None:
            return


        # if selected_indices:
        # Get the first selected index as it always returns a tuple
        index = selected_indices[0]
        # Get the actual value using the index
        selected_item = self.listbox.get(index)
        log_index = self.get_log_index_from_selections(self.listbox)

        room_name = self.selected_category.room_time_names[self.current_selected_actual_row]

        # Deletes the room entry then rebuilds the index
        # TODO figure out a more optimal way to rebuild indexes after every room entry deletes
        print(f'Deleting {room_name} with time {selected_item} room log entry on line {log_index}')
        room_time_from_log = read_funtoon_data.convert_framecount_to_seconds(
            self.sm.room_logs[log_index]['data']['practiceFrames'])
        print(room_time_from_log)

        previous_log_length = len(self.sm.room_logs)
        previous_index_num_of_entires = sum(len(row) for row in self.selected_category.run_category_indexes)
        print(f'Previous log length {previous_log_length}')
        if room_time_from_log != selected_item:
            raise ValueError(f'Room time {selected_item} does not match with time in logs {room_time_from_log}')

        del self.sm.room_logs[log_index]
        new_log_length = len(self.sm.room_logs)
        print(f'New log length {new_log_length}')
        if previous_log_length == new_log_length:
            raise RuntimeError(f"Failed to delete log entry {room_name} with time "
                               f"{selected_item} room log entry on line {log_index}")

        with open(self.sm.sm_files.room_log_file, 'w') as log_handler:
            for room in self.sm.room_logs:
                log_handler.write(json.dumps(room) + '\n')
        self.sm.rebuild_run_category_index(self.selected_category)

        new_index_num_of_entires = sum(len(row) for row in self.selected_category.run_category_indexes)
        print(f'Old number of index entires: {previous_index_num_of_entires}')
        print(f'New number of index entires: {new_index_num_of_entires}')

        #Refreshes all indexes and logs
        selected_room_to_restore = self.current_selected_actual_row
        self.refresh_tables()

    def get_log_index_from_selections(self, room_dropdown_menu, listbox, log_index_table):
        '''

        :param room_dropdown_menu:
        :param listbox:
        :param log_index_table:
        :return:
        '''
        row_index = room_dropdown_menu.current()
        # Get the first selected index (curselection() returns a tuple even for single select
        column_index = listbox.curselection()[0]
        return int(self.current_display_log_indexes[row_index][column_index])


    def refresh_tables(self):
        '''

        :return:
        '''
        previous_selected_actual_row = self.current_selected_actual_row
        # refresh best and average times table
        self.fastest_room_times = self.sm.get_fastest_room_times(self.selected_category)
        self.average_room_times = self.sm.get_average_room_times(self.selected_category)
        self.table_sheet = self._get_table_sheet()
        self.sheet.set_sheet_data(self.table_sheet)
        self.sheet.set_all_cell_sizes_to_text()

        if previous_selected_actual_row is not None and previous_selected_actual_row in self.actual_row_to_visible_row:
            self.root.after(1, lambda: self.select_room_by_actual_index(previous_selected_actual_row))
        elif self.visible_row_to_actual_row:
            self.root.after(1, lambda: self.select_room_by_actual_index(self.visible_row_to_actual_row[0]))
        else:
            self.current_selected_actual_row = None
            self.current_display_log_indexes = []
            self.listbox.delete(0, tkinter.END)
            self.room_name_label.config(text="None")
            self.room_time_label.config(text="Room Time: None")
            self.room_average_label.config(text="Average: None")
            self.room_pb_label.config(text="PB: None")



    def append_room_time(self, room_log):
        '''

        :param room_log:
        :return:
        '''
        print(json.dumps(room_log, indent=4))
        print(f'Writing to Log {self.sm.sm_files.room_log_file}')
        with open(self.sm.sm_files.room_log_file, 'a') as log_handler:
            log_handler.write(json.dumps(room_log) + '\n')
        print('Finished writing to Log')
        # append index and update table
        room_logic_index = self.sm.get_run_category_room_logic_index(room_log, self.selected_category)
        if room_logic_index is None and room_logic_index != 0:
            # self.selection_label.config(text=f'Unsupported room transition')
            self.room_name_label.config(text=f'Unsupported room transition')
            self.room_time_label.config(text="Room Time: None")
            self.room_average_label.config(text="Average: None")
            self.room_pb_label.config(text="PB: None")
            return

        #check if room time is a PB
        room_time_frames = room_log["data"]["practiceFrames"]
        room_time = read_funtoon_data.convert_framecount_to_seconds(room_time_frames)

        # Initlizes the PB to false.  Set it to true if there's a PB or not a first time room entry
        room_time_pb = False
        if self.fastest_room_times[room_logic_index]:
            if room_time_frames < read_funtoon_data.convert_room_time_to_framecount(
                    self.fastest_room_times[room_logic_index]):
                room_time_pb = True

        # self.sm.append_index_log(room_dict, self.selected_category)
        self.sm.room_logs = self.sm.sm_files.get_room_logs()
        last_log_index = len(self.sm.room_logs) - 1

        # Update category index list and file
        print(f'Writing to {self.selected_category.get_run_category_index_filename()}')

        #If log entry for that room is empty, initialize a list with that value
        if not self.selected_category.run_category_indexes[room_logic_index]:
            self.selected_category.run_category_indexes[room_logic_index] = [str(last_log_index)]
        else:
            print(f'Length of index {len(self.selected_category.run_category_indexes[room_logic_index])}')
            print(type(self.selected_category.run_category_indexes[room_logic_index][0]))
            print(self.selected_category.run_category_indexes[room_logic_index][0])

            self.selected_category.run_category_indexes[room_logic_index].append(str(last_log_index))
        with open(self.selected_category.get_run_category_index_filename(), 'w', newline='') as csvfile_handler:
            csvwriter = csv.writer(csvfile_handler)
            csvwriter.writerows(self.selected_category.run_category_indexes)

        # refresh best and average times table
        self.fastest_room_times = self.sm.get_fastest_room_times(self.selected_category)
        self.average_room_times = self.sm.get_average_room_times(self.selected_category)
        self.table_sheet = self._get_table_sheet()
        self.sheet.set_sheet_data(self.table_sheet)
        self.sheet.set_all_cell_sizes_to_text()
        # Change room selection and label

        self.root.after(1, lambda: self.select_room_by_actual_index(room_logic_index))

        room_name = self.selected_category.room_time_names[room_logic_index]
        self.room_name_label.config(text=room_name)
        self.room_time_label.config(text=f"Room Time: {room_time}")
        average_text = self.average_room_times[room_logic_index]
        self.room_average_label.config(text=f"Average: {average_text if average_text else 'None'}")

        pb_text = self.fastest_room_times[room_logic_index]
        # room_time_message = f'{self.room_dropdown_menu.get()}: {room_time}'
        if room_time_pb:
            self.room_pb_label.config(text=f"PB: {pb_text} *** NEW PB ***")
        else:
            self.room_pb_label.config(text=f"PB: {pb_text if pb_text else 'None'}")

    def websocket_thread_function(self):
        '''
        Main method to collect the funtoon data
        :param channel:
        :param token:
        :return:
        '''
        try:
            channel = self.channel_entry.get()
            token = self.api_token_entry.get()
            with connect(f'wss://funtoon.party/tracking?channel={channel}&token={token}') as ws:
                self.queue.put('Authenticated.  Waiting for Funtoon to detect the next room transition.')
                print('Connecting to funtoon')
                #Update config files
                if channel != self.sm.sm_files.roomtime_config['channel_name'] or \
                        token != self.sm.sm_files.roomtime_config['api_token']:
                    print(f'Updating config file {self.sm.sm_files.config_file}')
                    self.sm.sm_files.roomtime_config['channel_name'] = channel
                    self.sm.sm_files.roomtime_config['api_token'] = token
                    with open(self.sm.sm_files.config_file, 'w') as file_handler:
                        self.sm.sm_files.config.write(file_handler)

                msg = ws.recv()
                if msg == '"invalid auth"':
                    self.queue.put('invalid auth')
                    print('invalid auth')
                    return
                print(f'Connected to funtoon as {channel}')
                self.queue.put(f'Connected to funtoon as {channel}')
                while not self.stop_thread.is_set():
                    msg = ws.recv()
                    msg_obj = json.loads(msg)
                    event = msg_obj['event']
                    print(event)
                    if event == 'smRoomTime':
                        print(f'Pre-message type {type(msg_obj)}')
                        self.queue.put(msg_obj)

        except Exception as e:
            print(f"Error: {e}")
            traceback.print_exc()
        finally:
            self.queue.put("Disconnected")


