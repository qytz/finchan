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
"""
runtime Environment

the `env` object is a global singleton object,
other modules/extensions can access by just import it and can access/set attributes to `env` .
"""
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Union

from .dispatcher import Dispatcher
from .exts import ExtManager
from .utils import SingletonMeta

logger = logging.getLogger(__name__)


class ExtNameSpace(dict):
    def __init__(self):
        super().__init__()

    def __getattr__(self, key):
        return self.get(key, None)

    def __setattr__(self, key, val):
        self[key] = val


class Env(metaclass=SingletonMeta):
    """Global environment"""

    def __init__(self, *args, **kwargs):
        self.run_mode: str = None
        self.options = None
        self._dispathcer = None
        self._ext_manager = None
        self._work_dir = Path("~")
        self._ext_ns = ExtNameSpace()

    @property
    def now(self) -> datetime:
        """current datetime, wraps for dispatcher.now

        log is not permitted
        """
        if not self._dispathcer:
            return datetime.now()
        return self._dispathcer.now

    @property
    def dispatcher(self) -> Dispatcher:
        """the dispatcher manager object"""
        return self._dispathcer

    @property
    def ext_manager(self) -> ExtManager:
        """the extension manager object"""
        return self._ext_manager

    @property
    def ext_ns(self) -> ExtNameSpace:
        return self._ext_ns

    @property
    def work_dir(self) -> Path:
        return self._work_dir

    def set_work_dir(self, work_dir: Union[Path, str]) -> None:
        self._work_dir = Path(work_dir)

    def set_dispatcher(self, dispatcher: Dispatcher) -> bool:
        """set dispatcher object"""
        # from .dispatcher import Dispatcher
        # if not isinstance(dispatcher, Dispatcher):
        #     logger.warning('set env dispathcer failed, dispatcher is invalid: %s', dispatcher)
        #     return False
        self._dispathcer = dispatcher
        return True

    def set_ext_manager(self, ext_manager: ExtManager) -> bool:
        """set extension manager object"""
        # from .exts import ExtManager
        # if not isinstance(ext_manager, ExtManager):
        #     logger.warning('set env ext_manager failed, dispatcher is invalid: %s', ext_manager)
        #     return False
        self._ext_manager = ext_manager
        return True

    def get_ext_options(self, ext_name: str) -> Dict:
        """get options for extension named `ext` in configure file"""
        if not self.options or not self.options.get("exts", None):
            return {}
        return self.options["exts"].get(ext_name, {})

    def run(self):
        """wraps dispatcher's run"""
        if not self._dispathcer:
            logger.warning("No dispatcher setted, cannot run.")
            return None
        try:
            return asyncio.run(self._dispathcer.run())
        except AttributeError:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self._dispathcer.run())

    def load_exts(self, *exts: str) -> None:
        """load all the extensions in \*exts list"""
        if not self._ext_manager:
            logger.warning("call load_exts without setting ext_manager, no exts loaded")
        self._ext_manager.load_exts(*exts)


# sys.modules[__name__] = Env()
