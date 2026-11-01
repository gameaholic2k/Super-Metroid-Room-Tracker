import tkinter
from tkinter import ttk


class Options(ttk.Frame):
    def __init__(self, roomtime_config, parent_instance):
        self.parent_instance = parent_instance
        self.rom_type_radio_button_selection = tkinter.BooleanVar(value=True)
        self.run_category_menu_selection = tkinter.StringVar(value=roomtime_config['default_run_category'])
        self.run_category_combo_box = None

    def initialize_rom_type_options(self, parent_frame):
        rom_type_option_frame = ttk.Frame(parent_frame, padding=(5, 5))
        # rom_type_option_frame.grid(row=row, column=column, sticky="w", pady=(8, 0))
        ttk.Radiobutton(rom_type_option_frame,
                        text='Practice ROM',
                        variable=self.rom_type_radio_button_selection,
                        value=True,
                        command=self.parent_instance.on_rom_type_radio_button_selection).grid(row=0, column=1, sticky="w", padx=(50, 0), )
        ttk.Radiobutton(rom_type_option_frame,
                        text='Vanilla ROM',
                        variable=self.rom_type_radio_button_selection,
                        value=False,
                        command=self.parent_instance.on_rom_type_radio_button_selection).grid(row=1, column=1, sticky="w", padx=(50, 0))

        return rom_type_option_frame

    def initialize_run_category_menu_options(self, parent_frame, run_categories):
        run_category_names = []
        for category in run_categories:
            run_category_names.append(category)

        combo_box_frame = ttk.Frame(parent_frame)
        combo_box_label = ttk.Label(
            combo_box_frame,
            text='Run Categories',
            style="StatusTitle.TLabel"
        )
        self.run_category_combo_box = ttk.Combobox(combo_box_frame, values=run_category_names, state="readonly", textvariable=self.run_category_menu_selection)
        combo_box_label.pack(side=tkinter.TOP)
        self.run_category_combo_box.pack()
        return combo_box_frame

    def initialize_save_notes_button(self, parent_frame):
        save_notes_button = ttk.Button(
            parent_frame,
            # self.time_frame,
            text="Save Notes",
            command=self.parent_instance.on_save_notes_button_selection
        )
        return save_notes_button
