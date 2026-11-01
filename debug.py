import argparse
import file_loader
import json
import file_reader
from typing import Final


def get_room_name_with_address(sm_address_data, hex_address):
    for room in sm_address_data:
        if hex_address.upper() == room["value"].upper():
            return room["name"]
    return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Log index value grabber.")

    parser.add_argument("log_index", help="The first positional argument")
    parser.add_argument("rom_type", choices=['practice', 'vanilla', 'undefined'], help="The rom type of the log")
    parser.add_argument("category", help="Category of the run")

    # 3. Parse the arguments
    args = parser.parse_args()

    sm_files = file_loader.FileManager()
    all_run_categories: Final[list[str]] = sm_files.get_run_categories()
    log_handler = file_reader.RoomLogs(sm_files, all_run_categories)


    if args.rom_type == 'practice':
        time_key = 'practiceFrames'
        log_data = log_handler.logs.practice_logs
    else:
        time_key = 'frameCount'
        log_data = log_handler.logs.framecount_logs
        

    log_entry = log_data[int(args.log_index)]
    run_category = args.category.upper()

    print(json.dumps(log_entry, indent=4))
    run_category_instance = log_handler.run_category_instances[run_category]
    sm_address_data = run_category_instance.sm_address_data
    room_hex_address = hex(log_entry["data"]["roomID"])
    next_room_hex_address = hex(log_entry["data"]["nextRoomID"])
    room_name = get_room_name_with_address(sm_address_data, room_hex_address)
    next_room_name = get_room_name_with_address(sm_address_data, next_room_hex_address)

    formatted_time = file_reader.convert_framecount_to_seconds(log_entry["data"][time_key])

    room_path_logic_index = run_category_instance.get_run_category_room_logic_index(log_entry)
    if room_path_logic_index:
        individual_room_time_name = run_category_instance.room_time_names[room_path_logic_index]
    else:
        individual_room_time_name = None

    print(f'Room Name: {room_name}')
    print(f'Next Room Name: {next_room_name}')
    print(f'Room Time: {formatted_time}')
    print(f'Individual Room Name: {individual_room_time_name}')






