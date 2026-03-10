import re
import math
import dearpygui.dearpygui as dpg
import time
from collections import defaultdict
import copy

def add_ore_productions(ore_productions):
    total_ore_production = {
        "coal": 0,
        "iron-ore": 0,
        "copper-ore": 0,
        "stone": 0,
    }
    for ore_production in ore_productions:
        for ore, production in ore_production.items():
            total_ore_production[ore] += production
    return total_ore_production

def get_ore_production_in_lane(lane):
    return add_ore_productions([side["ore_ratio"] for pair in lane.values() for side in pair.values()])

def get_ore_production_in_layout(layout):
    return add_ore_productions([get_ore_production_in_lane(lane) for lane in layout.values() if lane])

def get_lane_miners_count(lane):
    miner_count = 0
    for pair in lane.values():
        miner_count += len(pair)
    return miner_count

def get_score(ore_production, ore_ratio_goal):
    ore_production_total = sum(ore_production.values())
    ore_ratio = {ore: production / ore_production_total for ore, production in ore_production.items()}
    return sum([abs(ore_ratio_goal[ore] - ratio) for ore, ratio in ore_ratio.items()])

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
all_miners = inf_dict()
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
                        all_miners[direction][offset_x][offset_y][lane][pair][side] = {
                            "ore_ratio": ore_count,
                            "position": miner_position
                        }

# solve
def solve(ore_ratio_goal):
    miners = copy.deepcopy(all_miners)
    t0 = time.perf_counter()
    for direction_key, direction in miners.items():
        for offset_x_key, offset_x in direction.items():
            for offset_y_key, offset_y in offset_x.items():
                offset = offset_y
                lanes_to_delete = []
                for lane_id, lane in offset.items():
                    lane_miners_count = get_lane_miners_count(lane)
                    if lane_miners_count < 30:
                        lanes_to_delete.append(lane_id)
                        continue
                    if lane_miners_count == 30:
                        continue
                    while True:
                        new_lane_miners_count = get_lane_miners_count(lane)
                        if new_lane_miners_count <= 30:
                            break
                        lane_ore_production = get_ore_production_in_lane(lane)
                        lane_score = get_score(lane_ore_production, ore_ratio_goal)
                        worst_miner_removed_lane_score = None
                        worst_miner_key = None
                        for pair_id, pair in lane.items():
                            for side_id, side in pair.items():
                                new_lane_ore_production = {ore: production - side["ore_ratio"][ore] for ore, production in lane_ore_production.items()}
                                new_lane_score = get_score(new_lane_ore_production, ore_ratio_goal)
                                if worst_miner_removed_lane_score is None or new_lane_score < worst_miner_removed_lane_score:
                                    worst_miner_removed_lane_score = new_lane_score
                                    worst_miner_key = (pair_id, side_id)
                        if worst_miner_key:
                            pair_id, side_id = worst_miner_key
                            del lane[pair_id][side_id]

                for lane_id in lanes_to_delete:
                    del offset[lane_id]

    layout_scores = []
    for direction, offset_xs in miners.items():
        for offset_x, offset_ys in offset_xs.items():
            for offset_y, layout in offset_ys.items():
                layout_ore_production = get_ore_production_in_layout(layout)
                layout_score = get_score(layout_ore_production, ore_ratio_goal)
                layout_scores.append(((direction, offset_x, offset_y), layout_score))
    layout_scores.sort(key=lambda x: x[1])

    t1 = time.perf_counter()
    print(f'Total solve time: {t1 - t0}s')

    return miners, layout_scores

# GUI

ui_configs = {
    "large": {
        "width": 1800,
        "height": 1400,
        "x_pos": 700,
        "y_pos": 400,
        "font_size": 20,
        "render_scale": 8,
    },
    "small": {
        "width": 1500,
        "height": 1000,
        "x_pos": 0,
        "y_pos": 0,
        "font_size": 15,
        "render_scale": 6,
    },
}

ui_config = ui_configs["large"]

dpg.create_context()
dpg.create_viewport(width=ui_config["width"], height=ui_config["height"], x_pos=ui_config["x_pos"], y_pos=ui_config["y_pos"], title="Weeeee", clear_color=(30, 30, 30))
dpg.setup_dearpygui()

with dpg.font_registry():
    default_font = dpg.add_font("FiraMono-Regular.ttf", ui_config["font_size"] * 2)
    dpg.bind_font(default_font)
    dpg.set_global_font_scale(0.5)

debug_info = {
    "position": None,
    "ore": None,
    "miner": None,
}

solved_miners = None

def update_miners_display(highlight_miner_position = None):
    direction = dpg.get_value("direction_combo")
    offset_x = dpg.get_value("offset_x_slider")
    offset_y = dpg.get_value("offset_y_slider")

    # Clear the drawlist (keep the background)
    dpg.delete_item("map_drawlist", children_only=True)

    # Draw background
    dpg.draw_rectangle(
        (0, 0),
        (bounding_box_size[0] * ui_config["render_scale"], bounding_box_size[1] * ui_config["render_scale"]),
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
            ((position[0] - bounding_box[0][0]) * ui_config["render_scale"], (position[1] - bounding_box[0][1]) * ui_config["render_scale"]),
            ((position[0] - bounding_box[0][0] + 1) * ui_config["render_scale"], (position[1] - bounding_box[0][1] + 1) * ui_config["render_scale"]),
            color=color,
            fill=color,
            parent="map_drawlist"
        )

    # Draw miners for selected configuration
    for lane_index, lane in all_miners[direction][offset_x][offset_y].items():
        has_miner_in_lane = False
        for pair_key, pair in lane.items():
            for side_key, side in pair.items():
                if solved_miners and solved_miners[direction][offset_x][offset_y][lane_index][pair_key][side_key]["position"]:
                    has_miner_in_lane = True
                    dpg.draw_rectangle(
                        ((side["position"][0] - bounding_box[0][0]) * ui_config["render_scale"], (side["position"][1] - bounding_box[0][1]) * ui_config["render_scale"]),
                        ((side["position"][0] + 3 - bounding_box[0][0]) * ui_config["render_scale"], (side["position"][1] + 3 - bounding_box[0][1]) * ui_config["render_scale"]),
                        color=(150, 255, 150, 192),
                        fill=(150, 255, 150, 48),
                        parent="map_drawlist"
                    )
                else:
                    dpg.draw_rectangle(
                        ((side["position"][0] - bounding_box[0][0]) * ui_config["render_scale"], (side["position"][1] - bounding_box[0][1]) * ui_config["render_scale"]),
                        ((side["position"][0] + 3 - bounding_box[0][0]) * ui_config["render_scale"], (side["position"][1] + 3 - bounding_box[0][1]) * ui_config["render_scale"]),
                        color=(255, 255, 255, 32),
                        fill=(255, 255, 255, 8),
                        parent="map_drawlist"
                    )
                if highlight_miner_position and \
                    lane_index == highlight_miner_position["lane_key"] and \
                    pair_key == highlight_miner_position["pair_key"] and \
                    side_key == highlight_miner_position["side_key"]:
                    dpg.draw_rectangle(
                        ((side["position"][0] - bounding_box[0][0]) * ui_config["render_scale"], (side["position"][1] - bounding_box[0][1]) * ui_config["render_scale"]),
                        ((side["position"][0] + 3 - bounding_box[0][0]) * ui_config["render_scale"], (side["position"][1] + 3 - bounding_box[0][1]) * ui_config["render_scale"]),
                        color=(255, 0, 0, 200),
                        fill=(255, 0, 0, 100),
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
                    (0, (lane_index * lane_width + offset_y + 3) * ui_config["render_scale"]),
                    (bounding_box_size[0] * ui_config["render_scale"], (lane_index * lane_width + offset_y + 3 + 1) * ui_config["render_scale"]),
                    **lane_args
                )
            else:
                dpg.draw_rectangle(
                    ((lane_index * lane_width + offset_x + 3) * ui_config["render_scale"], 0),
                    ((lane_index * lane_width + offset_x + 3 + 1) * ui_config["render_scale"], bounding_box_size[1] * ui_config["render_scale"]),
                    **lane_args
                )

def on_click_solve():
    global solved_miners
    coal = dpg.get_value("coal_slider")
    iron_ore = dpg.get_value("iron_ore_slider")
    copper_ore = dpg.get_value("copper_ore_slider")
    stone = dpg.get_value("stone_slider")
    total = coal + iron_ore + copper_ore + stone

    if total == 0:
        return

    solved_miners, layout_scores = solve({
        "coal": coal / total,
        "iron-ore": iron_ore / total,
        "copper-ore": copper_ore / total,
        "stone": stone / total,
    })

    update_miners_display()

    dpg.delete_item("results_table_group", children_only=True)
    with dpg.table(parent="results_table_group"):
        dpg.add_table_column(label="Layout")
        dpg.add_table_column(label="Score")
        for layout_score in [layout_score for layout_score in layout_scores if layout_score[0][0] == "horizontal"][:3]:
            with dpg.table_row():
                dpg.add_text(f'({layout_score[0][0][0]}, {layout_score[0][1]}, {layout_score[0][2]})')
                dpg.add_text(str(layout_score[1]))
        for layout_score in [layout_score for layout_score in layout_scores if layout_score[0][0] == "vertical"][:3]:
            with dpg.table_row():
                dpg.add_text(f'({layout_score[0][0][0]}, {layout_score[0][1]}, {layout_score[0][2]})')
                dpg.add_text(str(layout_score[1]))
    dpg.add_spacer(height=20, parent="results_table_group")

def on_click_map():
    click_position = dpg.get_drawing_mouse_pos()
    position = (click_position[0] // ui_config["render_scale"] + bounding_box[0][0], click_position[1] // ui_config["render_scale"] + bounding_box[0][1])

    direction = dpg.get_value("direction_combo")
    offset_x = dpg.get_value("offset_x_slider")
    offset_y = dpg.get_value("offset_y_slider")

    debug_info["position"] = position
    debug_info["ore"] = map[position] if position in map else ""
    debug_info["miner"] = None
    ore_production_in_lane = {}
    for lane_key, lane in all_miners[direction][offset_x][offset_y].items():
        for pair_key, pair in lane.items():
            for side_key, side in pair.items():
                miner_position = side["position"]
                if not miner_position:
                    continue
                if miner_position[0] <= position[0] < miner_position[0] + 3 and miner_position[1] <= position[1] < miner_position[1] + 3:
                    debug_info["miner"] = side
                    debug_info["lane"] = lane

                    ore_production_in_lane = get_ore_production_in_lane(lane)
                    update_miners_display({
                        "lane_key": lane_key,
                        "pair_key": pair_key,
                        "side_key": side_key,
                    })
                    break
    dpg.set_value("position_text", "position: " + str(debug_info["position"]))
    dpg.set_value("ore_text", "ore: " + str(debug_info["ore"]))
    dpg.set_value("miner_position_text", "  position: " + str(debug_info["miner"]["position"] if debug_info["miner"] else ""))
    dpg.set_value("miner_ore_ratio_text", "  ore ratio:\n    " + ("\n    ".join([f"{k}: {v}" for k, v in debug_info["miner"]["ore_ratio"].items()]) if debug_info["miner"] else ""))
    dpg.set_value("lane_ore_production_text", "  ore production:\n    " + ("\n    ".join([f"{k}: {v}" for k, v in ore_production_in_lane.items()]) if ore_production_in_lane else "")) 

with dpg.window(tag="root"):
    with dpg.group(horizontal=True):
        dpg.add_drawlist(
            width=bounding_box_size[0] * ui_config["render_scale"],
            height=bounding_box_size[1] * ui_config["render_scale"],
            callback=on_click_map,
            tag="map_drawlist"
        )

        with dpg.group(width=200):
            dpg.add_text("Target ore:")
            dpg.add_slider_int(label="Coal", tag="coal_slider")
            dpg.add_slider_int(label="Iron Ore", tag="iron_ore_slider")
            dpg.add_slider_int(label="Copper Ore", tag="copper_ore_slider")
            dpg.add_slider_int(label="Stone", tag="stone_slider")
            dpg.add_button(label="Solve", callback=on_click_solve)
            dpg.add_spacer(height=20)
            dpg.add_group(tag="results_table_group")
            dpg.add_combo(label="Direction", items=["vertical", "horizontal"], default_value="vertical", tag="direction_combo", callback=lambda: update_miners_display())
            dpg.add_slider_int(label="Offset X", min_value=0, max_value=6, tag="offset_x_slider", callback=lambda: update_miners_display())
            dpg.add_slider_int(label="Offset Y", min_value=0, max_value=6, tag="offset_y_slider", callback=lambda: update_miners_display())
            dpg.add_spacer(height=20)
            dpg.add_text("position: ", tag="position_text")
            dpg.add_text("ore: ", tag="ore_text")
            dpg.add_text("miner:")
            dpg.add_text("  position: ", tag="miner_position_text")
            dpg.add_text("  ore ratio: ", tag="miner_ore_ratio_text")
            dpg.add_text("lane:")
            dpg.add_text("  ore production: ", tag="lane_ore_production_text")

# Initial render
update_miners_display()

dpg.set_primary_window("root", True)
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()
