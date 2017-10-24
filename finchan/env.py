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

**this module MUSTNOT depend on any submodules of finchan, just avoid import loop.**

the `env` object is a global singleton object,
other modules/extensions can access by just import it and can access/set attributes to `env` .
"""
import logging
from datetime import datetime
from dateutil.parser import parse as parse_dt


logger = logging.getLogger(__name__)


class Env(object):
    """Global environment"""
    def __init__(self):
        self.run_mode = None
        self.options = None
        self._dispathcer = None
        self._ext_manager = None
        self._ext_objs = {}

    @property
    def now(self):
        """current datetime, wraps for dispatcher.now

        log is not permitted
        """
        if not self._dispathcer:
            return datetime.now()
        return self._dispathcer.now

    @property
    def dispatcher(self):
        """the dispatcher manager object"""
        return self._dispathcer

    @property
    def ext_manager(self):
        """the extension manager object"""
        return self._ext_manager

    def set_dispatcher(self, dispatcher):
        """set dispatcher object"""
        # from .dispatcher import Dispatcher
        # if not isinstance(dispatcher, Dispatcher):
        #     logger.warning('set env dispathcer failed, dispatcher is invalid: %s', dispatcher)
        #     return False
        self._dispathcer = dispatcher
        return True

    def set_ext_manager(self, ext_manager):
        """set extension manager object"""
        # from .exts import ExtManager
        # if not isinstance(ext_manager, ExtManager):
        #     logger.warning('set env ext_manager failed, dispatcher is invalid: %s', ext_manager)
        #     return False
        self._ext_manager = ext_manager
        return True

    def set_ext_obj(self, ext, obj):
        """set object for ext

        :param ext: name of the extension.
        :param obj: the object that call be access globaly by all.
        """
        self._ext_objs[ext] = obj

    def get_ext_obj(self, ext):
        """get object for ext that setted.

        :param ext: name of the extension.
        :return: the obj that the extension setted.
        """
        return self._ext_objs.get(ext, None)

    def get_ext_options(self, ext):
        """get options for extension named `ext` in configure file"""
        if not self.options:
            return {}
        if self.run_mode == 'backtrack':
            ext_dict = self.options.get('backtrack_exts', None)
        else:
            ext_dict = self.options.get('live_track_exts', None)
        if not ext_dict:
            return {}
        return ext_dict.get(ext, {})

    def run(self):
        """wraps dispatcher's run"""
        if not self._dispathcer:
            logger.warning('No dispatcher setted, cannot run.')
            return None
        return self._dispathcer.dispatch()

    def load_exts(self, *exts):
        """load all the extensions in \*exts list"""
        if not self._ext_manager:
            logger.warning('call load_exts without setting ext_manager, no exts loaded')
        self._ext_manager.load_exts(*exts)


env = Env()
