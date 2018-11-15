# -*- coding: utf-8 -*-
# This file is part of finchan.

# Copyright (C) 2017-present qytz <hhhhhf@foxmail.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""options manager"""
from pathlib import Path
from ruamel.yaml import YAML

yaml = YAML(typ="safe", pure=True)
# yaml.default_flow_style = False


def parse_yaml_conf(conf_path):
    """parse yaml option file with finchan options.

    return a dict with all options in it.
    """
    try:
        return yaml.load(Path(conf_path))
    except Exception as e:
        raise SyntaxError("load configure file failed: %s" % str(e))


def merge_configs(a, b):
    """deep merge dict configs from b to a

    merge all dict&list values, recursely, will modify a object and return"""
    if type(a) != type(b):
        raise TypeError("Different type of merge objects: %s<=>%s" % (type(a), type(b)))

    if not isinstance(a, (list, dict)):
        raise TypeError("can only merge dict/list, get %s" % type(a))

    if isinstance(a, list):
        for val in b:
            if val not in a:
                a.append(val)
    else:
        for key, val in b.items():
            if key not in a:
                a[key] = val
                continue

            if not isinstance(a[key], type(val)):
                raise TypeError(
                    "Different types for key %s found: %s<=>%s"
                    % (key, type(a), type(b))
                )

            if isinstance(val, (list, dict)):
                merge_configs(a[key], val)
            else:
                raise TypeError(
                    "can only merge dict/list, get %s for key %s" % (type(val), key)
                )
    return a


def load_configs(conf_path):
    """load yaml configure files from a path, support one file and multiple configure files in the path"""
    p = Path(conf_path).expanduser()
    if p.is_file():
        return parse_yaml_conf(p)

    configs = [parse_yaml_conf(f) for f in p.rglob("*.yml")]

    merged_config = {}
    for config in configs:
        if not config:  # skip empty configure file
            continue
        merge_configs(merged_config, config)
    return merged_config
