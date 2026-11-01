import tkinter
from typing import Final

class DropDownMenuBar:
    COLORED_SHEETS: Final[str] = "Colored Sheets"
    BACKGROUND_COLOR: Final[str] = "Enable Background Color"
    HIDE_NOTES: Final[str] = "Hide Notes"
    HIDE_EMPTY_ROWS: Final[str] = "Hide Empty Rows"
    EXTRA_OPTIONS: Final[str] = "Extra Options"
    UPDATE_ITEM_COLLECTION_TIMES: Final[str] = "Update Item Collection Times"
    def __init__(self, parent_root, roomtime_config, run_categories: dict[str, bool]):
        self.is_background_color_menu_check = tkinter.BooleanVar(value=roomtime_config.getboolean('enable_colored_background'))
        self.is_colored_sheet_menu_check = tkinter.BooleanVar(value=roomtime_config.getboolean('colored_sheets'))
        self.is_hide_empty_rows_menu_check = tkinter.BooleanVar(value=roomtime_config.getboolean('hide_empty_rows'))
        self.is_hide_notes_menu_check = tkinter.BooleanVar(value=roomtime_config.getboolean('hide_notes'))
        self.menubar = tkinter.Menu(parent_root)
        parent_root.config(menu=self.menubar)

        self.view_options_menu = tkinter.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="View Options", menu=self.view_options_menu)

        self.view_options_menu.add_checkbutton(label=self.BACKGROUND_COLOR, variable=self.is_background_color_menu_check)
        self.view_options_menu.add_checkbutton(label=self.COLORED_SHEETS, variable=self.is_colored_sheet_menu_check)
        self.view_options_menu.add_checkbutton(label=self.HIDE_NOTES, variable=self.is_hide_notes_menu_check)
        self.view_options_menu.add_checkbutton(label=self.HIDE_EMPTY_ROWS, variable=self.is_hide_empty_rows_menu_check)

        # Enabled Categories
        self.enabled_categories_menu = tkinter.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Enabled Run Categories", menu=self.enabled_categories_menu)
        self.category_vars: dict[str, tkinter.BooleanVar] = {}
        for category, is_checked in run_categories.items():
            var = tkinter.BooleanVar(value=is_checked)
            self.category_vars[category] = var
            self.enabled_categories_menu.add_checkbutton(label=category, variable=var)

        # Extra options
        self.extra_options_menu = tkinter.Menu(self.menubar, tearoff=0)
        self.extra_options_menu.add_command(label=self.UPDATE_ITEM_COLLECTION_TIMES)
