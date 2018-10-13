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
"""Extension manager"""
import os
import sys
import logging
from importlib import import_module
from collections import OrderedDict


logger = logging.getLogger(__name__)


class add_to_syspath(object):
    """A context for add a directory to sys.path for a second."""

    def __init__(self, path, prepend=True):
        self.added = False
        self.path = path
        self.prepend = prepend

    def __enter__(self):
        if self.path and self.path not in sys.path:
            if self.prepend:
                sys.path.insert(0, self.path)
            else:
                sys.path.append(self.path)
            self.added = True

    def __exit__(self, type, value, traceback):
        if self.added:
            try:
                sys.path.remove(self.path)
            except ValueError:
                pass
        # Returning False causes any exceptions to be re-raised.
        return False


class ExtManager(object):
    """Extension manager for finchan.

    An finchan extension is an importable Python module that has
    a function with the signature::

        def load_finchan_ext(*args, **kwargs):
            # Do setup

    This function is called after your extension is imported.
    \*args and \*\*kwargs is passed from configure file's `config.live_track_exts` or
    `config.backtrack_exts` 's extension module name section depend on the run mode.

    You can also optionally define an :func:`unload_finchan_ext()`
    function, which will be called if the user unloads the extension.

    You can put your extension modules anywhere you want, as long as
    they can be imported by Python's standard import mechanism.  However,
    to make it easy to write extensions, you can also put your extensions
    in a configured path `config.ext_path`.
    This directory is added to ``sys.path`` automatically.
    """
    def __init__(self, env, ext_path='', **kwargs):
        self.env = env
        self._ext_path = ext_path
        self._loaded_exts = OrderedDict()

    def load_exts(self, exts):
        """load exts for finchan:

        :param exts: exts dict, key is extension name, value is extension kwargs
        """
        logger.info('#Extm loading exts...')
        with add_to_syspath(self._ext_path):
            for ext_name in exts:
                logger.info('#Extm loading ext %s...', ext_name)
                if ext_name in self._loaded_exts:
                    logger.warning('Ext[%s] has been loaded: %s, skip...',
                                   ext_name,
                                   self._loaded_exts[ext_name])
                    continue
                ext = import_module(ext_name)
                if not hasattr(ext, 'load_finchan_ext'):
                    logger.warning('Invalid ext[%s] for finchan: %s', ext_name, ext)
                    continue
                try:
                    kwargs = dict(exts[ext_name])
                    ext.load_finchan_ext(self.env, **kwargs)
                except ValueError:
                    args = list(exts[ext_name])
                    ext.load_finchan_ext(self.env, *args)
                except TypeError:
                    ext.load_finchan_ext(self.env)
                self._loaded_exts[ext_name] = ext
                logger.info('#Extm ext[%s] loaded.', ext_name)

    def unload_exts(self, *exts):
        """unload exts for finchan

        :param exts: ext_name args list
        """
        logger.info('#Extm unloading exts...')
        for ext_name in exts:
            logger.info('#Extm unloading ext %s...', ext_name)
            if ext_name not in self._loaded_exts:
                logger.warning('Ext[%s] has not been loaded, skip...', ext_name)
                continue
            ext = self._loaded_exts[ext_name]
            if not hasattr(ext, 'unload_finchan_ext'):
                logger.warning('Ext[%s] has no unload func, skip...', ext_name)
                continue
            ext.unload_finchan_ext(self.env)
            del self._loaded_exts[ext_name]
            logger.info('#Extm ext[%s] loaded.', ext_name)
