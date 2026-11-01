import json
from dataclasses import dataclass


@dataclass
class SheetColors:
    cell_color: str
    text_color: str

@dataclass
class RoomSetting:
    color_data: SheetColors
    notes: str = ''

def generate_user_data(room_definiton: dict) -> list[dict]:
    category = room_definiton['category']
    new_data = []
    for index, room in enumerate(room_definiton['roomDefinitionList']):
        try:
            room_id = room['data']['roomID']
        except TypeError:
            room_id = None

        room_region = get_room_setting_from_room_id(room_id=room_id, index=index, category=category)
        new_data.append(
                {'individual_room_time_name': room['names']['individual_room_time_name'],
                'row': index+1,
                'cell_color': room_region.color_data.cell_color,
                'text_color': room_region.color_data.text_color,
                 'notes': room_region.notes,},
                    )
    return new_data

def get_text_override(room_index):
    text_overrides = {
        0: "Don't bonk the door",
        1: "Don't bonk the door",
        2: "Don't bonk the door",
        3: "Don't bonk the door",
        4: "Don't bonk the door",
        5: "Don't bonk the door\nBonk Ridley's tail",
        6: "Don't bonk the door",
        7: "Don't bonk the door",
        8: "Don't bonk the door",
        9: "Don't bonk the door",
    }
    if room_index in text_overrides.keys():
        return text_overrides[room_index]
    return ''

def get_room_setting_from_room_id(room_id: int | None, index: int, category: str) -> RoomSetting:
    crateria_blue_brin_addresses = [
            0x91F8,
            0x92B3,
            0x92FD,
            0x93AA,
            0x93D5,
            0x93FE,
            0x9461,
            0x948C,
            0x94CC,
            0x94FD,
            0x9552,
            0x957D,
            0x95A8,
            0x95D4,
            0x95FF,
            0x962A,
            0x965B,
            0x968F,
            0x96BA,
            0x975C,
            0x97B5,
            0x9804,
            0x9879,
            0x98E2,
            0x990D,
            0x9938,
            0x9969,
            0x9994,
            0x99BD,
            0x99F9,
            0x9A44,
            0x9A90,
            0x9E9F,
            0x9F11,
            0xA107,
            0x9F64,
            0xA1AD,
            0xA1D8,
            0xA66A,
            0xA5ED
    ]

    brinstar_addresses = [
            0x9AD9,
            0x9B5B,
            0x9B9D,
            0x9BC8,
            0x9C07,
            0x9C35,
            0x9C5E,
            0x9C89,
            0x9CB3,
            0x9D19,
            0x9D9C,
            0x9DC7,
            0x9E11,
            0x9E52,
            0x9FBA,
            0x9FE5,
            0xA011,
            0xA051,
            0xA07B,
            0xA0A4,
            0xA0D2,
            0xA130,
            0xA15B,
            0xA184,
            0xA201,
            0xA22A,
            0xA253,
            0xA293,
            0xA2CE,
            0xA2F7,
            0xA322,
            0xA37C,
            0xA3AE,
            0xA3DD,
            0xA408,
            0xA447,
            0xA734
    ]

    kraid_warehouse_addresses = [
            0xA471,
            0xA4B1,
            0xA4DA,
            0xA521,
            0xA56B,
            0xA59F,
            0xA618,
            0xA641,
            0xA6A1,
            0xA6E2,
            0xA70B
    ]

    upper_norfair_addresses = [
            0xA75D,
            0xA788,
            0xA7B3,
            0xA7DE,
            0xA815,
            0xA865,
            0xA890,
            0xA8B9,
            0xA8F8,
            0xA923,
            0xA98D,
            0xA9E5,
            0xAA0E,
            0xAA41,
            0xAA82,
            0xAAB5,
            0xAADE,
            0xAB07,
            0xAB3B,
            0xAB64,
            0xAB8F,
            0xABD2,
            0xAC00,
            0xAC2B,
            0xAC5A,
            0xAC83,
            0xACB3,
            0xACF0,
            0xAD1B,
            0xAD5E,
            0xADAD,
            0xADDE,
            0xAE07,
            0xAE32,
            0xAE74,
            0xAEB4,
            0xAEDF,
            0xAF14,
            0xAF3F,
            0xAF3F,
            0xAF72,
            0xAFA3,
            0xAFCE,
            0xAFFB,
            0xB026,
            0xB051,
            0xB07A,
            0xB0B4,
            0xB0DD,
            0xB106,
            0xB139,
            0xB167,
            0xB192,
            0xB1BB,
            0xB1E5
    ]

    lower_norfair_addresses = [
            0xB236,
            0xB283,
            0xB2DA,
            0xB305,
            0xB32E,
            0xB37A,
            0xB3A5,
            0xB3E1,
            0xB40A,
            0xB457,
            0xB482,
            0xB4AD,
            0xB4E5,
            0xB510,
            0xB55A,
            0xB585,
            0xB5D5,
            0xB62B,
            0xB656,
            0xB698,
            0xB6C1,
            0xB6EE,
            0xB741
    ]

    wrecked_ship_addresses = [
            0xC98E,
            0xCA08,
            0xCA52,
            0xCAAE,
            0xCAF6,
            0xCB8B,
            0xCBD5,
            0xCC27,
            0xCC6F,
            0xCCCB,
            0xCD13,
            0xCD5C,
            0xCDA8,
            0xCDF1,
            0xCE40,
            0xCE8A
    ]

    maradia_addresses = [
            0xCED2,
            0xCEFB,
            0xCF54,
            0xCF80,
            0xCFC9,
            0xD017,
            0xD055,
            0xD08A,
            0xD0B9,
            0xD104,
            0xD13B,
            0xD16D,
            0xD1A3,
            0xD1DD,
            0xD21C,
            0xD252,
            0xD27E,
            0xD2AA,
            0xD2D9,
            0xD30B,
            0xD340,
            0xD387,
            0xD3B6,
            0xD3DF,
            0xD408,
            0xD433,
            0xD461,
            0xD48E,
            0xD4C2,
            0xD4EF,
            0xD51E,
            0xD54D,
            0xD57A,
            0xD5A7,
            0xD5EC,
            0xD617,
            0xD646,
            0xD69A,
            0xD6D0,
            0xD6FD,
            0xD72A,
            0xD765,
            0xD78F,
            0xD7E4,
            0xD81A,
            0xD845,
            0xD86E,
            0xD898,
            0xD8C5,
            0xD913,
            0xD95E,
            0xD9AA,
            0xD9D4,
            0xD9FE,
            0xDA2B,
            0xDA60
    ]

    tourian_addresses = [
            0xDAAE,
            0xDAE1,
            0xDB31,
            0xDB7D,
            0xDBCD,
            0xDC19,
            0xDC65,
            0xDCB1,
            0xDCFF,
            0xDD2E,
            0xDD58,
            0xDD58,
            0xDDC4,
            0xDDF3,
            0xDE23,
            0xDE4D,
            0xDE7A,
            0xDEA7,
            0xDEDE,
            0xDF1B
    ]

    ceres_addresses = [
            0xDF45,
            0xDF8D,
            0xDFD7,
            0xE021,
            0xE06B,
            0xE0B5,
            0xE82C
    ]

    ceres_colors = SheetColors(cell_color='#FFD966',
                              text_color='#000000')
    crateria_blue_brin_colors = SheetColors(cell_color='#8E7CC3',
                                           text_color='#FFFFFF')
    brinstar_colors = SheetColors(cell_color='#93C47D',
                                 text_color='#000000')
    kraid_warehouse_colors = SheetColors(cell_color='#6AA84F',
                                        text_color='#000000')
    upper_norfair_colors = SheetColors(cell_color='#FF9031',
                                      text_color='#000000')
    wrecked_ship_colors = SheetColors(cell_color='#666666',
                                     text_color='#FFFFFF')
    maradia_colors = SheetColors(cell_color='#1155CC',
                                text_color='#FFFFFF')
    lower_norfair_colors = SheetColors(cell_color='#E06666',
                                      text_color='#000000')
    tourian_colors = SheetColors(cell_color='#741B47',
                                text_color='#FFFFFF')
    default_colors = SheetColors(cell_color = '#FFFFFF',
                                text_color = '#000000')

    kprd_upper_norfair_lower_route_colors = SheetColors(cell_color='#F6B26B',
                                            text_color='#000000')

    ceres = {}
    for address in ceres_addresses:
        ceres[address] = ceres_colors
    crateria_blue_brin = {}
    for address in crateria_blue_brin_addresses:
        crateria_blue_brin[address] = crateria_blue_brin_colors
    brinstar = {}
    for address in brinstar_addresses:
        brinstar[address] = brinstar_colors
    kraid_warehouse = {}
    for address in kraid_warehouse_addresses:
        kraid_warehouse[address] = kraid_warehouse_colors
    upper_norfair = {}
    for address in upper_norfair_addresses:
        upper_norfair[address] = upper_norfair_colors
    wrecked_ship = {}
    for address in wrecked_ship_addresses:
        wrecked_ship[address] = wrecked_ship_colors
    maradia = {}
    for address in maradia_addresses:
        maradia[address] = maradia_colors
    lower_norfair = {}
    for address in lower_norfair_addresses:
        lower_norfair[address] = lower_norfair_colors
    tourian = {}
    for address in tourian_addresses:
        tourian[address] = tourian_colors

    region_data = [ceres, crateria_blue_brin, brinstar, kraid_warehouse, upper_norfair, wrecked_ship,
                   maradia, lower_norfair, tourian]

    kpdr_override: dict[int, SheetColors] = {
        186: kprd_upper_norfair_lower_route_colors,
        187: kprd_upper_norfair_lower_route_colors,
        188: kprd_upper_norfair_lower_route_colors,
        189: kprd_upper_norfair_lower_route_colors,
        190: kprd_upper_norfair_lower_route_colors,
        191: kprd_upper_norfair_lower_route_colors,
        192: kprd_upper_norfair_lower_route_colors,
        193: kprd_upper_norfair_lower_route_colors,
        13: crateria_blue_brin_colors,
        176: upper_norfair_colors,
        201: lower_norfair_colors,
        112: wrecked_ship_colors,
        113: wrecked_ship_colors,
    }

    pkrd_override: dict[int, SheetColors] = {
        13: crateria_blue_brin_colors,
        58: wrecked_ship_colors,
        59: wrecked_ship_colors,
    }
    category_overrides = {'KPDR': kpdr_override,
                          'PRKD': pkrd_override}
    for region in region_data:
        if category_overrides.get(category):
            if index in category_overrides[category].keys():
                return RoomSetting(color_data=category_overrides[category][index], notes=get_text_override(index))
        if room_id in region.keys():
            return RoomSetting(color_data=region[room_id], notes=get_text_override(index))

    return RoomSetting(color_data=default_colors, notes=get_text_override(index))