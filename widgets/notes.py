import tkinter
from tkinter import ttk


def _initialize_save_notes_button(parent_frame):
    save_notes_button = ttk.Button(
        parent_frame,
        text="Save Notes"
    )
    return save_notes_button


class Notes:
    def __init__(self, parent_frame, roomtime_config):
        self.notes_frame = ttk.Frame(parent_frame)
        self.is_notes_editable = tkinter.BooleanVar(value=roomtime_config.getboolean('hide_notes'))

        self.room_note_label = ttk.Label(
            self.notes_frame,
            text='Notes',
            style="StatusValue.TLabel",
            font=("TkDefaultFont", 16, "bold")
        )
        self.room_note_label.pack()

        self.text_frame = tkinter.Text(self.notes_frame, wrap=tkinter.WORD)
        self.text_frame.pack(fill=tkinter.BOTH, expand=True)
        self.text_frame.config(state=tkinter.DISABLED)
        self.notes_config_frame = ttk.Frame(self.notes_frame)
        self.notes_config_frame.pack(anchor=tkinter.W)
        self.edit_notes_checkbox = self._initialize_edit_notes_checkbox_options(self.notes_config_frame)
        self.edit_notes_checkbox.pack(side=tkinter.LEFT)
        self.save_notes_button = _initialize_save_notes_button(self.notes_config_frame)
        self.save_notes_button.pack(anchor=tkinter.W, padx=(20, 0))


    def _initialize_edit_notes_checkbox_options(self, parent_frame):
        edit_notes_checkbox = ttk.Checkbutton(
            parent_frame,
            text="Edit Notes",
            variable=self.is_notes_editable)
        return edit_notes_checkbox
