import re
import math
import dearpygui.dearpygui as dpg
from collections import defaultdict

RENDER_SCALE = 8

file = open('ores.txt', 'r')
if not file:
    print("Error opening file: ores.txt")
    exit()

map = {} # position at the top-left point
bounding_box = ((None, None), (None, None))
for match in re.findall(r'{name = "([a-zA-Z \-]+)", position = {x = (-?\d+\.?\d*), y = (-?\d+\.?\d*)}}', file.read()):
    position = (math.floor(float(match[1])), math.floor(float(match[2])))
    map[position] = match[0]
    if bounding_box[0][0] is None or position[0] < bounding_box[0][0]:
        bounding_box = ((position[0], bounding_box[0][1]), bounding_box[1])
    elif bounding_box[1][0] is None or position[0] > bounding_box[1][0]:
        bounding_box = (bounding_box[0], (position[0], bounding_box[1][1]))
    elif bounding_box[0][1] is None or position[1] < bounding_box[0][1]:
        bounding_box = ((bounding_box[0][0], position[1]), bounding_box[1])
    elif bounding_box[1][1] is None or position[1] > bounding_box[1][1]:
        bounding_box = (bounding_box[0], (bounding_box[1][0], position[1]))
padding = 7
bounding_box = ((bounding_box[0][0] - padding, bounding_box[0][1] - padding), (bounding_box[1][0] + padding, bounding_box[1][1] + padding))
bounding_box_size = (bounding_box[1][0] - bounding_box[0][0], bounding_box[1][1] - bounding_box[0][1])

# structure: horizontal/vertial - offsetx - offsety - lane - pair - side - {ore_ratio, position}
inf_dict = lambda: defaultdict(inf_dict)
miners = inf_dict()
for direction in ["horizontal", "vertical"]:
    lane_width = 7
    pair_width = 3
    x_step, y_step = direction == "horizontal" and (pair_width, lane_width) or (lane_width, pair_width)
    for offset_x in range(0, x_step):
        for offset_y in range(0, y_step):
            for lane in range(0, bounding_box_size[1] // lane_width):
                for pair in range(0, bounding_box_size[0] // pair_width):
                    for side in range(0, 2):
                        # horizontal
                        miner_position = direction == "horizontal" \
                            and (bounding_box[0][0] + offset_x + pair * 3, bounding_box[0][1] + offset_y + lane * lane_width + side * 4) \
                            or (bounding_box[0][0] + offset_x + lane * lane_width + side * 4, bounding_box[0][1] + offset_y + pair * 3)
                        miner_effect_bounding_box = (
                            (miner_position[0] - 1, miner_position[1] - 1),
                            (miner_position[0] + 3 + 1, miner_position[1] + 3 + 1)
                        )
                        ore_count = {
                            "coal": 0,
                            "iron-ore": 0,
                            "copper-ore": 0,
                            "stone": 0
                        }
                        for x in range(miner_effect_bounding_box[0][0], miner_effect_bounding_box[1][0]):
                            for y in range(miner_effect_bounding_box[0][1], miner_effect_bounding_box[1][1]):
                                if (x, y) in map and map[(x, y)] in ["coal", "iron-ore", "copper-ore", "stone"]:
                                    ore_count[map[(x, y)]] += 1
                        total_ore_count = sum(ore_count.values())
                        if total_ore_count == 0:
                            continue
                        for ore, count in ore_count.items():
                            ore_count[ore] = count / total_ore_count
                        miners[direction][offset_x][offset_y][lane][pair][side] = {
                            "ore_ratio": ore_count,
                            "position": miner_position
                        }

# GUI

dpg.create_context()
dpg.create_viewport(width=1600, height=1400, x_pos=500, y_pos=200, title="Weeeee")
dpg.setup_dearpygui()

debug_info = {
    "position": None,
    "ore": None,
    "miner": None,
}

def update_miners_display():
    """Redraw miners based on current input values"""
    direction = dpg.get_value("direction_combo")
    offset_x = dpg.get_value("offset_x_slider")
    offset_y = dpg.get_value("offset_y_slider")

    # Clear the drawlist (keep the background)
    dpg.delete_item("map_drawlist", children_only=True)

    # Draw background
    dpg.draw_rectangle(
        (0, 0),
        (bounding_box_size[0] * RENDER_SCALE, bounding_box_size[1] * RENDER_SCALE),
        fill=(64, 64, 64),
        parent="map_drawlist"
    )

    # Draw ore tiles
    for position, name in map.items():
        if name == "coal":
            color = (0, 0, 0)
        elif name == "iron-ore":
            color = (104, 130, 144)
        elif name == "copper-ore":
            color = (200, 98, 48)
        elif name == "stone":
            color = (176, 152, 104)
        else:
            continue
        dpg.draw_rectangle(
            ((position[0] - bounding_box[0][0]) * RENDER_SCALE, (position[1] - bounding_box[0][1]) * RENDER_SCALE),
            ((position[0] - bounding_box[0][0] + 1) * RENDER_SCALE, (position[1] - bounding_box[0][1] + 1) * RENDER_SCALE),
            color=color,
            fill=color,
            parent="map_drawlist"
        )

    # Draw miners for selected configuration
    for lane_index, lane in miners[direction][offset_x][offset_y].items():
        has_miner_in_lane = False
        for pair in lane.values():
            for side in pair.values():
                has_miner_in_lane = True
                dpg.draw_rectangle(
                    ((side["position"][0] - bounding_box[0][0]) * RENDER_SCALE, (side["position"][1] - bounding_box[0][1]) * RENDER_SCALE),
                    ((side["position"][0] + 3 - bounding_box[0][0]) * RENDER_SCALE, (side["position"][1] + 3 - bounding_box[0][1]) * RENDER_SCALE),
                    color=(255, 255, 255, 128),
                    fill=(255, 255, 255, 32),
                    parent="map_drawlist"
                )
        if has_miner_in_lane:
            lane_args = {
                "color": (200, 160, 64, 64),
                "fill": (200, 160, 64, 32),
                "parent": "map_drawlist"
            }
            if direction == "horizontal":
                dpg.draw_rectangle(
                    (0, (lane_index * lane_width + offset_y + 3) * RENDER_SCALE),
                    (bounding_box_size[0] * RENDER_SCALE, (lane_index * lane_width + offset_y + 3 + 1) * RENDER_SCALE),
                    **lane_args
                )
            else:
                dpg.draw_rectangle(
                    ((lane_index * lane_width + offset_x + 3) * RENDER_SCALE, 0),
                    ((lane_index * lane_width + offset_x + 3 + 1) * RENDER_SCALE, bounding_box_size[1] * RENDER_SCALE),
                    **lane_args
                )

def click_handler():
    click_position = dpg.get_drawing_mouse_pos()
    position = (click_position[0] // RENDER_SCALE + bounding_box[0][0], click_position[1] // RENDER_SCALE + bounding_box[0][1])

    direction = dpg.get_value("direction_combo")
    offset_x = dpg.get_value("offset_x_slider")
    offset_y = dpg.get_value("offset_y_slider")

    debug_info["position"] = position
    debug_info["ore"] = map[position] if position in map else "None"
    debug_info["miner"] = None
    for lane in miners[direction][offset_x][offset_y].values():
        for pair in lane.values():
            for side in pair.values():
                miner_position = side["position"]
                if miner_position[0] <= position[0] < miner_position[0] + 3 and miner_position[1] <= position[1] < miner_position[1] + 3:
                    debug_info["miner"] = side
                    break
    dpg.set_value("position_text", "position: " + str(debug_info["position"]))
    dpg.set_value("ore_text", "ore: " + str(debug_info["ore"]))
    dpg.set_value("miner_position_text", "  position: " + str(debug_info["miner"]["position"] if debug_info["miner"] else None))
    dpg.set_value("miner_ore_ratio_text", "  ore ratio:\n    " + ("\n    ".join([f"{k}: {v}" for k, v in debug_info["miner"]["ore_ratio"].items()]) if debug_info["miner"] else "None"))

with dpg.window(label="Map", autosize=True):
    with dpg.drawlist(
        width=bounding_box_size[0] * RENDER_SCALE,
        height=bounding_box_size[1] * RENDER_SCALE,
        callback=click_handler,
        tag="map_drawlist"
    ):
        pass

with dpg.window(label="Debug", pos=(bounding_box_size[0] * RENDER_SCALE + 30, 0), autosize=True):
    dpg.add_combo(label="Direction", items=["vertical", "horizontal"], default_value="vertical", tag="direction_combo", callback=lambda: update_miners_display())
    dpg.add_slider_int(label="Offset X", min_value=0, max_value=6, tag="offset_x_slider", callback=lambda: update_miners_display())
    dpg.add_slider_int(label="Offset Y", min_value=0, max_value=6, tag="offset_y_slider", callback=lambda: update_miners_display())
    dpg.add_text("Click on the map to see positional info here.")
    dpg.add_text("")
    dpg.add_text("position: ", tag="position_text")
    dpg.add_text("ore: ", tag="ore_text")
    dpg.add_text("miner:")
    dpg.add_text("  position: ", tag="miner_position_text")
    dpg.add_text("  ore ratio: ", tag="miner_ore_ratio_text")

# Initial render
update_miners_display()

dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()
