import tkinter
from tkinter import ttk
from tksheet import Sheet

class RoomTimesSheet:
    def __init__(self, parent_frame):
        self.sheet_frame = ttk.Frame(parent_frame)
        self.sheet = Sheet(self.sheet_frame)

        self.sheet.headers(["Room Name", "Fastest Session", "Average Time"])
        self.sheet.set_all_cell_sizes_to_text()
        self.sheet.enable_bindings((
            'single_select',
            'row_select',
            'column_select',
            'select_rows',
            'drag_select',
            'copy',
            'arrowkeys',
        ))
        self.sheet.pack(side=tkinter.LEFT, fill=tkinter.BOTH, expand=True)