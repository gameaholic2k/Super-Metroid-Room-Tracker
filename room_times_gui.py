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

@dataclass
class FrameData:
    index: int
    frame_count: str


class RoomTimeTrackerGUI:

    def __init__(self):

        self.sm = read_funtoon_data.SuperMetroidRooms()
        #TODO select last saved category from config file
        self.selected_category = self.sm.run_categories[0]
        self.fastest_room_times = self.sm.get_fastest_room_times(self.selected_category)
        self.average_room_times = self.sm.get_average_room_times(self.selected_category)
        self.room_time_names = self.selected_category.get_room_time_names()
        self.table_sheet = self._get_table_sheet(self.room_time_names, self.fastest_room_times, self.average_room_times)
        self.log_handler = None

        #TODO create another class for storing widgets
        self.root = tkinter.Tk()
        self.root.title("Room Time Tracker")

        #Styles
        self.ttk_style = ttk.Style()
        self.ttk_style.configure('Red.TLabel', foreground='red')
        self.ttk_style.configure('Orange.TLabel', foreground='orange')
        self.ttk_style.configure('Green.TLabel', foreground='green')

        # Create a top frame
        self.top_frame = tkinter.Frame(self.root)
        self.top_frame.pack(side=tkinter.TOP, fill=tkinter.BOTH, expand=True, padx=10, pady=5)

        # Create a right frame
        self.right_frame = tkinter.Frame(self.root)
        self.right_frame.pack(side=tkinter.RIGHT, fill=tkinter.BOTH, expand=True, padx=10, pady=5)

        # Create a bottom frame
        self.bottom_frame = tkinter.Frame(self.root)
        self.bottom_frame.pack(side=tkinter.BOTTOM, fill=tkinter.BOTH, expand=True, padx=10, pady=5)

        # Channel label
        self.channel_label = ttk.Label(self.top_frame, text="Twitch Channel Name:")
        self.channel_label.grid(row=0, column=0, padx=5, pady=5)

        # Channel Entry Widget
        # The key is the 'show="*" ' option
        self.channel_entry = ttk.Entry(self.top_frame)
        self.channel_entry.grid(row=1, column=0, padx=5, pady=5)
        self.channel_entry.focus() # Set focus to the entry box initially
        self.channel_entry.insert(0, self.sm.sm_files.channel_name)

        # API Token label
        self.api_token_label = ttk.Label(self.top_frame, text="FUNtoon API Token:")
        self.api_token_label.grid(row=0, column=1, padx=5, pady=5)

        # API Entry Widget
        # The key is the 'show="*" ' option
        self.api_token_entry = ttk.Entry(self.top_frame, show="*")
        self.api_token_entry.grid(row=1, column=1, padx=5, pady=5)
        self.api_token_entry.focus() # Set focus to the entry box initially
        self.api_token_entry.insert(0, self.sm.sm_files.api_token)

        self.connect_button = ttk.Button(self.top_frame, text="Connect", command=self.on_button_click_connect)
        self.connect_button.grid(row=0, column=2, padx=5, pady=5)

        # Spreadsheet for times
        self.sheet = Sheet(self.bottom_frame, height=500, width=700)
        self.sheet.grid(row=0, column=0, padx=5, pady=5)

        self.sheet.headers(["Room name", "Fastest Time", "Average Time"]) 
        self.sheet.set_sheet_data(self.table_sheet)
        self.sheet.set_all_cell_sizes_to_text()
        self.sheet.enable_bindings((
            "single_select",  # Allow selecting single cells
            "row_select",     # Allow selecting full rows
            "column_select",  # Allow selecting full columns
            "select_rows",    # Enable row selection
            "drag_select",    # Enable drag selection
            "copy",           # Enable copy spreadsheet
        ))

        # Listbox for roomtimes
        self.listbox = tkinter.Listbox(self.right_frame, selectmode=tkinter.SINGLE) # height sets the number of lines visible
        # listbox.pack(pady=10, padx=10, fill=ttk.BOTH, expand=True)
        self.listbox.grid(row=1, column=0, padx=5, pady=5)

        # Attach a scrollbar (optional, but recommended for long lists)
        self.scrollbar = ttk.Scrollbar(self.root, orient=tkinter.VERTICAL, command=self.listbox.yview)
        self.scrollbar.pack(side=tkinter.RIGHT, fill=tkinter.Y)
        self.listbox.config(yscrollcommand=self.scrollbar.set)

        # Add a button to show the selected value
        # self.select_button = ttk.Button(self.right_frame, text="Delete selected room log", command=lambda: self.show_selection(self.selected_category.run_category_indexes, self.sm.room_logs))
        self.select_button = ttk.Button(self.right_frame, text="Delete selected room log", command=self.delete_entry)
        self.select_button.grid(row=3, column=0, padx=5, pady=5)

        # Add a label to display the selection result
        self.selection_label = ttk.Label(self.right_frame, text="Selected: None")
        self.selection_label.grid(row=4, column=0, padx=5, pady=5)

        # Drop down menu for rooms
        self.room_dropdown_menu = ttk.Combobox(self.right_frame, state='readonly', values=self.room_time_names)
        self.room_dropdown_menu.grid(row=0, column=0, padx=5, pady=5)
        self.room_dropdown_menu.bind("<<ComboboxSelected>>", self.dropdown_menu_select)

        self.stop_thread = threading.Event()
        self.thread = None

        self.status_label = ttk.Label(self.root, text="Status: Disconnected", style='Red.TLabel')
        self.status_label.pack()

        self.root.mainloop()


    def on_button_click_connect(self):
        '''
        Starts the websocket connection thread which is triggered from the connect button
        :return: None
        '''
        if self.api_token_entry.get() and self.channel_entry.get():
            if self.thread is None or not self.thread.is_alive():
                self.stop_thread.clear()
                self.thread = threading.Thread(target=self.websocket_thread_function, daemon=True, args=(self.channel_entry.get(), self.api_token_entry.get()))
                self.thread.start()
                self.status_label.config(text="Status: Connecting...", style='Orange.TLabel')
                self.connect_button.config(state=tkinter.DISABLED)
            else:
                self.stop_thread.set()
                self.status_label.config(text="Status: Disconnecting...", style='Red.TLabel')
                self.connect_button.config(state=tkinter.NORMAL)

    def _get_table_sheet(self, room_time_names, fastest_room_times, average_room_times):
        '''

        :param room_time_names:
        :param fastest_room_times:
        :param average_room_times:
        :return:
        '''
        table_sheet = []
        for index, room in enumerate(room_time_names):
            table_sheet.append([room, fastest_room_times[index], average_room_times[index]])
        return table_sheet

    # def dropdown_menu_select(self, event, room_times):
    def dropdown_menu_select(self, event):
        '''

        :param event:
        :return: None
        '''
        self.listbox.delete(0, tkinter.END)
        run_category_index = self.room_dropdown_menu.current()
        room_times = self.sm.get_room_times_from_index(self.selected_category)

        # Combine the lists into tuples, sort by the first element (sorted_room_times),
        # and unzip them back into separate variables.
        # Then apply the changes to the run category index
        # sorted_room_times, sorted_category_index = zip(*sorted(zip(room_times[run_category_index], self.selected_category.run_category_indexes[run_category_index])))

        if not room_times[run_category_index]:
            return
        # Combine lists into a list of tuples, sort based on the first element of the tuples (sorted_room_times), then unzip
        print(room_times[run_category_index])
        print(self.selected_category.run_category_indexes[run_category_index])
        sorted_pairs = sorted(zip(room_times[run_category_index], self.selected_category.run_category_indexes[run_category_index]))
        # Unpack the sorted pairs back into two separate tuples
        sorted_room_times, sorted_category_index = zip(*sorted_pairs)

        # Convert tuples back to lists
        sorted_room_times = list(sorted_room_times)
        sorted_category_index = list(sorted_category_index)
        self.selected_category.run_category_indexes[run_category_index] = sorted_category_index
        for room_time in sorted_room_times:
            self.listbox.insert(tkinter.END, read_funtoon_data.convert_framecount_to_seconds(room_time))

    def delete_entry(self):
        '''
        Deletes the room time entry.  Index needs to be rebuilt after every entry is deleted
        :return: None
        '''
        selected_indices = self.listbox.curselection()
        if selected_indices:
            # Get the first selected index as it always returns a tuple
            index = selected_indices[0]
            # Get the actual value using the index
            selected_item = self.listbox.get(index)
            log_index = self.get_log_index_from_selections(self.room_dropdown_menu, self.listbox, self.selected_category.run_category_indexes)

            # Deletes the room entry then rebuilds the index
            # TODO figure out a more optimal way to rebuild indexes after every room entry deletes
            print(f'Deleting {self.room_dropdown_menu.get()} with time {selected_item} room log entry on line {log_index}')
            room_time_from_log = read_funtoon_data.convert_framecount_to_seconds(self.sm.room_logs[log_index]['data']['practiceFrames'])
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
                raise RuntimeError(f"Failed to delete log entry {self.room_dropdown_menu.get()} with time {selected_item} room log entry on line {log_index}")

            with open(self.sm.sm_files.room_log_file, 'w') as log_handler:
                for room in self.sm.room_logs:
                    log_handler.write(json.dumps(room) + '\n')
            self.sm.rebuild_run_category_index(self.selected_category)

            new_index_num_of_entires = sum(len(row) for row in self.selected_category.run_category_indexes)
            print(f'Old number of index entires: {previous_index_num_of_entires}')
            print(f'New number of index entires: {new_index_num_of_entires}')

            #Refreshes all indexes and logs
            self.refresh_tables()

        else:
            self.selection_label.config(text="No item selected")

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
        return int(log_index_table[row_index][column_index])


    def refresh_tables(self):
        '''

        :return:
        '''
        # refresh best and average times table
        self.fastest_room_times = self.sm.get_fastest_room_times(self.selected_category)
        self.average_room_times = self.sm.get_average_room_times(self.selected_category)
        self.table_sheet = self._get_table_sheet(self.room_time_names, self.fastest_room_times, self.average_room_times)
        self.sheet.set_sheet_data(self.table_sheet)
        # Change room selection and label
        self.dropdown_menu_select(None)

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
        if not room_logic_index:
            self.selection_label.config(text='Room transition not implemented or not applicable to current category')
            return

        #check if room time is a PB
        room_time = read_funtoon_data.convert_framecount_to_seconds(room_log["data"]["practiceFrames"])

        if room_time < self.fastest_room_times[room_logic_index]:
            room_time_pb = True
        else:
            room_time_pb = False

        # self.sm.append_index_log(room_dict, self.selected_category)
        self.sm.room_logs = self.sm.sm_files.get_room_logs()
        last_log_index = len(self.sm.room_logs) - 1

        # Update category index list and file
        print(f'Writing to {self.selected_category.get_run_category_index_filename()}')

        #If log entry for that room is empty, initialize a list with that value
        # if is_deeply_empty(self.selected_category.run_category_indexes[room_logic_index]):
        # if '[]' in self.selected_category.run_category_indexes[room_logic_index]:
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
        self.table_sheet = self._get_table_sheet(self.room_time_names, self.fastest_room_times, self.average_room_times)
        self.sheet.set_sheet_data(self.table_sheet)
        self.sheet.set_all_cell_sizes_to_text()
        # Change room selection and label
        self.room_dropdown_menu.current(room_logic_index)
        self.dropdown_menu_select(None)

        if room_time_pb:
            room_time_message = f'{self.room_dropdown_menu.get()}: {room_time} ****NEW PB*****'
        else:
            room_time_message = f'{self.room_dropdown_menu.get()}: {room_time}'

        self.selection_label.config(text=room_time_message)

    def websocket_thread_function(self, channel, token):
        '''
        Main method to collect the funtoon data
        :param channel:
        :param token:
        :return:
        '''
        try:
            with connect(f'wss://funtoon.party/tracking?channel={channel}&token={token}') as ws:
                self.status_label.config(text=f"Authenticated.  Waiting for Funtoon to detect the next room transition.", style='Orange.TLabel')
                print('Connecting to funtoon')
                #Update config files
                if channel != self.sm.sm_files.roomtime_config['channel_name'] or token != self.sm.sm_files.roomtime_config['api_token']:
                    print(f'Updating config file {self.sm.sm_files.config_file}')
                    self.sm.sm_files.roomtime_config['channel_name'] = channel
                    self.sm.sm_files.roomtime_config['api_token'] = token
                    with open(self.sm.sm_files.config_file, 'w') as file_handler:
                        self.sm.sm_files.config.write(file_handler)

                print(self.stop_thread.is_set())
                ws.send('test')
                while not self.stop_thread.is_set():
                    print('test')
                    msg = ws.recv()
                    print(msg)
                    if msg == '"invalid auth"':
                        self.status_label.config(text=f"invalid auth")
                        print('invalid auth')
                        return
                    print(f'Connected to funtoon as {channel}')
                    self.status_label.config(text=f'Connected to funtoon as {channel}', style='Green.TLabel')
                    self.connect_button.config(state=tkinter.DISABLED)
                    msgObj = json.loads(msg)
                    event = msgObj['event']
                    print(event)
                    if event == 'smRoomTime':
                        room_log = {'timestamp': time.time(),
                                     'data': msgObj['data']}
                        self.append_room_time(room_log)

        except Exception as e:
            self.status_label.config(text=f"Error: {e}")
            print(f"Error: {e}")
            traceback.print_exc()
        finally:
            # self.message_queue.put("Disconnected")
            self.status_label.config(text=f"Disconnected", style='Red.TLabel')
            self.connect_button.config(state=tkinter.NORMAL)

