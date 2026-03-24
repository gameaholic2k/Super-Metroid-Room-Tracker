import csv
from collections import Counter, defaultdict, OrderedDict
# room_time_csv = 'no_strat.csv'

# room_times_dict = {}
# with open(room_time_csv) as csvfile:
#     room_transition_idx = 0
#     room_time_idx = 1
#     roomtime_reader = csv.reader(csvfile)
#
#     for row in roomtime_reader:
#         room_transition = row[room_transition_idx]
#         if room_times_dict.get(room_transition):
#             #print(type(room_times_dict[room_transition]))
#             if float(row[room_time_idx]) < float(room_times_dict[room_transition]):
#                 room_times_dict[room_transition] = row[room_time_idx]
#         else:
#             room_times_dict[room_transition] = row[room_time_idx]
#
#
#     for row in room_times_dict:
#         print(row)
import json
import math
import configparser
from websockets.sync.client import connect
# from gooey import Gooey, GooeyParser
import os
import time
from collections import Counter, OrderedDict
from datetime import datetime
import asyncio
# def update_room_times(output_file, room_data):
#     # Check if the file is empty or doesn't exist
#     if not os.path.exists(filename) or os.stat(filename).st_size == 0:
#         with open(output_file, 'a+') as f:




async def connect_to_funtoon(token, channel, log_handler):
    with connect(f'wss://funtoon.party/tracking?channel={channel}&token={token}', proxy='http://proxy-chain.intel.com:912') as ws:
        print(f'Connected to funtoon as {channel}')
        #Update config files

        #grey out connect button
        # connect_button.config(state='disabled')
        while True:
            msg = ws.recv()
            print(msg)
            if msg == '"invalid auth"':
                return
            msgObj = json.loads(msg)
            event = msgObj['event']
            print(event)
            if event == 'smRoomTime':
                room_dict = {}
                room_dict['timestamp'] = time.time()
                room_dict['data'] = msgObj['data']
                #room_data = msgObj['data']

                # Write the updated list back to the file
                os.system('cls')
                print(json.dumps(room_dict, indent=4))
                log_handler.write(json.dumps(room_dict) + '\n')
                #append index
                #Change room selection and label




output_file = "list_of_roomtimes.jsonl"
channel = "gameaholic2d"
token = "FXoOUawDv0Gu8I1lsFVpnhIjRCtfhHmmsS5ASAktndm"
# connect_to_funtoon(output_file, channel, token)
asyncio.run(connect_to_funtoon(output_file, channel, token))
print("test")