"""This module contains method to read config files and build pipeline using processors module."""
from typing import List
import yaml


def read_config(filepath: str):
    with open(filepath) as file:
        config = yaml.safe_load(file)

    return config


def parse_config(config):
    # stages: List[str] = config['stages']
    objects = list(filter(lambda x: x != 'stages', config.keys()))
    del config['stages']

    outputs = []
    function_names = []
    step_names = []
    input_names = []
    i = 0

    while i < len(objects):
        obj_name = objects[i]
        step_params = config[obj_name]

        if step_params.get('function', False):
            function_names.append(obj_name)
            i += 1
            continue
        else:
            step_names.append(obj_name)

        if not step_params.get("inputs", False):
            input_names.append(obj_name)
            outputs.extend(step_params.get("outputs") or [])
            i += 1
            continue

        # sort the functions in such a way that the input of each function has a predetermined output
        is_okey = True
        for input_edge in step_params.get("inputs"):
            if input_edge not in outputs:
                if i == len(objects) - 1:  # last element can't be swapped so it's error in config
                    raise AttributeError(
                        f"Can't connect {obj_name} to the graph:",
                        f"didn't find {input_edge} as output at previous stages."
                    )
                objects[i], objects[i + 1] = objects[i + 1], objects[i]
                is_okey = False

        if is_okey:
            outputs.extend(step_params.get("outputs") or [])  # finish node in graph may not containes outputs
            i += 1

    return {
        "functions": function_names,
        "names": step_names,
        "config": config
    }


def handle_config(config_path: str):
    config = read_config(config_path)
    return parse_config(config)
