import tkinter
from tkinter import ttk

class DeleteQueue:
    def __init__(self, parent_frame):
        self.delete_queue_frame = ttk.Frame(parent_frame)
        self.delete_queue_label = ttk.Label(
            self.delete_queue_frame,
            text='Delete Queue',
            style="StatusValue.TLabel",
            font=("TkDefaultFont", 16, "bold")
        )
        self.delete_queue_label.pack()

        self.delete_queue_listbox = tkinter.Listbox(self.delete_queue_frame, selectmode=tkinter.SINGLE)
        self.delete_queue_listbox.pack(fill=tkinter.BOTH, expand=True)

        self.delete_queue_button_frame = ttk.Frame(self.delete_queue_frame)

        self.remove_queue_button = ttk.Button(self.delete_queue_frame, text="Cancel selected item from queue",)
        self.batch_delete_button = ttk.Button(self.delete_queue_frame, text="Batch Delete")
        self.remove_queue_button.pack(side=tkinter.LEFT)
        self.batch_delete_button.pack(side=tkinter.RIGHT)