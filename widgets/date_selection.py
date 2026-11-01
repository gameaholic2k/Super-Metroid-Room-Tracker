import tkinter
from tkinter import ttk
from typing import Final

class DateSelection:
    ALL_TIMES: Final[str] = 'All Times'
    CURRENT_SESSION: Final[str] = 'Current Session'
    WEEKLY: Final[str] = 'Weekly'
    MONTHLY: Final[str] = 'Monthly'
    LAST_N_DAYS: Final[str] = 'Last N Days'
    def __init__(self, parent_frame, roomtime_config):
        self.date_selection_frame = ttk.Frame(parent_frame)
        self.time_units_selection = tkinter.StringVar(value=roomtime_config['time_units'])

        self.all_times_option = ttk.Radiobutton(self.date_selection_frame, text=self.ALL_TIMES, variable=self.time_units_selection, value=self.ALL_TIMES)
        self.all_times_option.pack(side="left", padx=(0,15))

        self.daily_option = ttk.Radiobutton(self.date_selection_frame, text=self.CURRENT_SESSION, variable=self.time_units_selection, value=self.CURRENT_SESSION)
        self.daily_option.pack(side="left", padx=(0,15))

        self.weekly_option = ttk.Radiobutton(self.date_selection_frame, text=self.WEEKLY, variable=self.time_units_selection, value=self.WEEKLY)
        self.weekly_option.pack(side="left", padx=(0,15))

        self.monthly_option = ttk.Radiobutton(self.date_selection_frame, text=self.MONTHLY, variable=self.time_units_selection, value=self.MONTHLY)
        self.monthly_option.pack(side="left", padx=(0,30))

        self.last_num_of_days_option = ttk.Radiobutton(self.date_selection_frame,text=self.LAST_N_DAYS, variable=self.time_units_selection, value=self.LAST_N_DAYS)
        self.last_num_of_days_option.pack(side="left")

        self.num_of_days_entry = tkinter.Entry(self.date_selection_frame)
        self.num_of_days_entry.pack(side="left")
        self.num_of_days_entry.insert(0, roomtime_config['num_of_days'])

        self.set_button = ttk.Button(self.date_selection_frame, text="Set")
        self.set_button.pack(side="left")

        if self.time_units_selection.get() != self.LAST_N_DAYS:
            self.num_of_days_entry.config(state=tkinter.DISABLED)
            self.set_button.config(state=tkinter.DISABLED)



