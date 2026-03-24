import os
import json
from pathlib import Path
import read_funtoon_data





def validate_room_definitions(room_definition_list, room_logs, room_address_definitions, state_definitions):
     for index, room in enumerate(room_logs):
        counter = []
        for room_definition in room_definition_list:
            room_data_match = read_funtoon_data.compare_room_data(room_definition, room, room_address_definitions, state_definitions)
            if room_data_match is True:
                counter.append(room_definition)

        room_name = read_funtoon_data.get_room_name_with_address(hex(room['data']['roomID']), room_address_definitions)
        next_room_name = read_funtoon_data.get_room_name_with_address(hex(room['data']['nextRoomID']), room_address_definitions)
        room_id = room['data']['roomID']
        next_room_id = room['data']['nextRoomID']

        if len(counter) < 1:
            print(f"No definitions found in index {index} for room {room_name} ({room_id} / {hex(room_id)}) -> {next_room_name } ({next_room_id} / {hex(next_room_id)})")


            show_indexes_from_room_path_ids(room_id, next_room_id, room_definition_list)

        elif len(counter) > 1:
            print(f"Duplicate entires found in index {index} for room {room_name} ({room_id} / {hex(room_id)}) -> {next_room_name } ({next_room_id} / {hex(next_room_id)})")
            for entry in counter:
                print(json.dumps(entry, indent=4))
            print(json.dumps(room, indent=4))

            




def debug_room_log(room_definition_list, room_logs, room_address_definitions, state_definitions, log_idx, definition_idx):
    room = room_logs[log_idx]
    room_definition = room_definition_list[definition_idx]
    # print('Room Log:')
    # print(print(json.dumps(room, indent=4)))
    # print("Room Definition: ")
    # print(print(json.dumps(room_definition, indent=4)))

    print(read_funtoon_data.compare_room_data(room_definition, room, room_address_definitions, state_definitions, debug=True))


def get_idx_value_from_room_definition(room_definition_list, sub_definition):
    for index, room_definition in enumerate(room_definition_list):
        if read_funtoon_data.is_subset_dict(sub_definition, room_definition):
            print(f'match found on index: {index}')


def show_indexes_from_room_path_ids(room_id, next_room_id, room_definition_list):
    for index, room_definition in enumerate(room_definition_list):
        if room_definition['data']:
            if room_definition['data']['roomID'] == room_id and room_definition['data']['nextRoomID'] == next_room_id:
                room_time_name = room_definition['names']['individual_room_time_name']
                print(f'Possible match for room: {room_time_name} on index {index}')
    print('\n')


def check_definition_ids(definition_list, room_address_definitions):
    for index, room_definition in enumerate(definition_list):
        if not 'not_yet_implemented' in room_definition:
            definition_room_id = room_definition['data']['roomID']
            definition_next_room_id = room_definition['data']['nextRoomID']
            print(f'{room_definition['names']['individual_room_time_name']}')
            current_room = f'Room: {room_definition['names']['room']} ({definition_room_id} {hex(definition_next_room_id)})'
            next_room = f'Next Room: {room_definition['names']['nextRoom']} ({definition_next_room_id} {hex(definition_next_room_id)})'
            print(f'{current_room} / {next_room}')
            #
            room_name = read_funtoon_data.get_room_name_with_address(hex(definition_room_id), room_address_definitions)
            next_room_name = read_funtoon_data.get_room_name_with_address(hex(definition_next_room_id), room_address_definitions)
            print(f'{room_name} / {next_room_name}')
            print('\n')



category_directory = 'categories'
category_directory_path = os.path.join(Path(__file__).resolve().parent, category_directory)
room_log_file = 'list_of_roomtimes.jsonl'
address_file = 'SuperMetroid.json'
state_definition_file = 'game_state.json'
category = 'KPDR'

definition_list = read_funtoon_data.get_category_definitions(category, category_directory_path)
room_logs = read_funtoon_data.get_room_logs(room_log_file)
with open(address_file) as f:
    room_address_definitions = json.load(f)['definitions']
with open(state_definition_file) as f:
    state_definitions = json.load(f)



test_definition = {
            "names": {
                "individual_room_time_name": "Draygon",
                "room": "Draygon's Room",
                "nextRoom": "Space Jump Room"
            },
            "data": {
                "roomID": 55904,
                "nextRoomID": 55722,
				"exitState": {
					"spikeSuit": False
				}
            }
}




def validate_category_definitions(definitions, address_definitions):
    for room in definitions:
         if not 'not_yet_implemented' in room:
            current_room = room['names']['room']
            current_room_id = room['data']['roomID']
            next_room = room['names']['nextRoom']
            next_room_id = room['data']['nextRoomID']
            address_room_name = read_funtoon_data.get_room_name_with_address(hex(current_room_id), address_definitions)
            next_address_room_name = read_funtoon_data.get_room_name_with_address(hex(next_room_id), address_definitions)
            if current_room != address_room_name:
                print(f'{room["names"]["individual_room_time_name"]}')
                print(f"Mismatch room name {current_room} / {address_room_name}")
            if next_room != next_address_room_name:
                print(f'{room["names"]["individual_room_time_name"]}')
                print(f"Mismatch next room name {next_room} / {next_address_room_name}")
  




#debug_room_log(definition_list, room_logs, room_address_definitions, state_definitions, log_idx=137, definition_idx=148)

#get_idx_value_from_room_definition(definition_list, test_definition)
# '141'
#validate_room_definitions(definition_list, room_logs, room_address_definitions, state_definitions)
#check_definition_ids(definition_list, room_address_definitions)

#validate_category_definitions(definition_list, room_address_definitions)

room_definition_indexes = {}
for index, definition in enumerate(definition_list):
    if not 'not_yet_implemented' in definition:
        room_indexes = []
        room_destination_key = f'{definition["data"]["roomID"]}->{definition["data"]["nextRoomID"]}'
        if room_destination_key not in room_definition_indexes:
            room_definition_indexes[room_destination_key] = [index]
        else:
            room_definition_indexes[room_destination_key].append(index)

print(room_definition_indexes)