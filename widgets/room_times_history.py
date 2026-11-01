import tkinter
from tkinter import ttk

class RoomTimesHistory:
    def __init__(self, parent_frame):
        self.room_history_frame = ttk.Frame(parent_frame)
        self.listbox = tkinter.Listbox(self.room_history_frame, selectmode=tkinter.MULTIPLE)
        self.summary_header = ttk.Label(
            self.room_history_frame,
            text="Selected Room History",
            style="PanelHeader.TLabel"
        )
        self.summary_header.grid(row=0, column=0, sticky="w", pady=(0, 8))
        self.listbox.grid(row=1, column=0, sticky="nsew")
        self.scrollbar = ttk.Scrollbar(
            self.room_history_frame,
            orient=tkinter.VERTICAL,
            command=self.listbox.yview
        )
        self.scrollbar.grid(row=1, column=1, sticky="ns")
        self.listbox.config(yscrollcommand=self.scrollbar.set)

        self.add_delete_queue_button = ttk.Button(
            self.room_history_frame,
            text="Add to delete queue"
        )
        self.add_delete_queue_button.grid(row=2, column=0, pady=(8, 4))

        self.room_history_frame.rowconfigure(1, weight=1)
        self.room_history_frame.columnconfigure(0, weight=1)
        self.room_history_frame.grid_columnconfigure(0, weight=1)