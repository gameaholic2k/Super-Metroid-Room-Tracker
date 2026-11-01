import tkinter as tk
from tkinter import ttk
from pathlib import Path
import configparser
import logging

logger = logging.getLogger(__name__)

def disable_event():
    pass

def initialize_category_popup_window(root: tk.Tk,
                                     run_category_names: list,
                                     config: configparser.ConfigParser,
                                     config_file: Path):
    popup = tk.Toplevel(root)
    popup.title("Initial setup")
    popup.geometry("300x150")

    popup.grab_set()
    popup.attributes('-topmost', True)

    label = tk.Label(popup, text="Select at least one category to track", pady=10)
    label.pack()

    checkbox_vars: dict[str, tk.BooleanVar] = {}
    for category in run_category_names:
        var = tk.BooleanVar()
        checkbox_vars[category] = var
        ttk.Checkbutton(popup, text=category, variable=var).pack()


    ok_button = tk.Button(popup, text="Confirm", command=lambda: on_click_ok_button(popup, checkbox_vars, config, config_file))
    popup.protocol("WM_DELETE_WINDOW", disable_event)

    ok_button.pack(pady=10)

    root.wait_window(popup)

def on_click_ok_button(popup_window: tk.Toplevel, run_category_check_vars: dict[str, tk.BooleanVar], config: configparser.ConfigParser, config_file: Path):
    if True in [var.get() for var in run_category_check_vars.values()]:
        checked_items = [key for key, value in run_category_check_vars.items() if value.get() == True]
        checked_categories = ','.join(checked_items)
        config['roomtime_config']['enabled_categories'] = checked_categories
        with open(config_file, 'w') as file_handler:
            config.write(file_handler)
        popup_window.destroy()