import tkinter
from tkinter import ttk

class SummaryFrame:
    def __init__(self, parent_frame):
        self.summary_frame = ttk.Frame(parent_frame)
        self.room_name_frame = ttk.Frame(self.summary_frame)
        self.room_time_frame = ttk.Frame(self.summary_frame)

        self.room_name_label = ttk.Label(
            self.room_name_frame,
            text="None",
            style="StatusValue.TLabel",
            font=("TkDefaultFont", 16, "bold")
        )
        self.room_name_label.pack()

        self.room_time_label = ttk.Label(
            self.room_time_frame,
            text="Current room time: None",
            style="StatusTitle.TLabel"
        )
        self.room_time_label.pack(side=tkinter.LEFT)

        self.room_average_label = ttk.Label(
            self.room_time_frame,
            text="Average: None",
            style="StatusTitle.TLabel"
        )
        self.room_average_label.pack(side=tkinter.LEFT, padx=(20, 0))

        self.room_pb_label = ttk.Label(
            self.room_time_frame,
            text="PB: None",
            style="StatusTitle.TLabel"
        )
        self.room_pb_label.pack(side=tkinter.LEFT, padx=(20, 0))
        self.room_name_frame.pack(anchor=tkinter.NW)
        self.room_time_frame.pack(anchor=tkinter.NW)
