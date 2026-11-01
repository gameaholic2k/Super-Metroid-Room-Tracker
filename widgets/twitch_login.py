import tkinter
from tkinter import ttk


class TwitchLogin:
    def __init__(self, parent_frame, roomtime_config):
        self.is_auto_connect = tkinter.BooleanVar(value=roomtime_config.getboolean('auto_connect'))
        self.twitch_login_frame = ttk.Frame(parent_frame)
        self.twitch_credential_frame = ttk.Frame(self.twitch_login_frame)
        self.twitch_credential_frame.pack()

        self.twitch_status_frame = ttk.Frame(self.twitch_login_frame)
        self.twitch_status_frame.pack()

        self.channel_label = ttk.Label(self.twitch_credential_frame, text="Twitch Channel Name:")
        self.channel_label.grid(row=0, column=0, padx=(0, 5), pady=2, sticky="w")

        self.channel_entry = ttk.Entry(self.twitch_credential_frame)
        self.channel_entry.grid(row=0, column=1, padx=(0, 12), pady=2, sticky="ew")
        self.channel_entry.insert(0, roomtime_config['channel_name'])

        self.api_token_label = ttk.Label(self.twitch_credential_frame, text="FUNtoon API Token:")
        self.api_token_label.grid(row=1, column=0, padx=(0, 5), pady=2, sticky="w")

        self.api_token_entry = ttk.Entry(self.twitch_credential_frame, show="*")
        self.api_token_entry.grid(row=1, column=1, padx=(0, 12), pady=2, sticky="ew")
        self.api_token_entry.insert(0, roomtime_config['api_token'])

        self.connect_button = ttk.Button(
            self.twitch_credential_frame,
            text="Connect",
        )
        self.connect_button.grid(row=0, column=2, padx=(0, 12), pady=2, sticky="w")

        self.status_label = ttk.Label(
            self.twitch_status_frame,
            text="Status: Disconnected",
            style="Red.TLabel",
            anchor="w"
        )
        self.status_label.grid(row=0, column=0, sticky="w", pady=2, rowspan=3)

        self.auto_connect_checkbox = ttk.Checkbutton(
            self.twitch_credential_frame,
            text="Auto Connect",
            variable=self.is_auto_connect,
        )
        self.auto_connect_checkbox.grid(row=1, column=2, padx=(0, 12), pady=2, sticky="w")


        self.channel_entry.focus()
