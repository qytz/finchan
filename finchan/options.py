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

yaml=YAML()
yaml.default_flow_style = False


def parse_yaml_conf(conf_path):
    """parse yaml option file with finchan options.

    return a dict with all options in it."""
    return yaml.load(Path(conf_path))
