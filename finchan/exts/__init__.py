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
import logging
import sys
from collections import OrderedDict
from importlib import import_module

logger = logging.getLogger(__name__)


class add_to_syspath(object):
    """A context for add a directory to sys.path for a second."""

    def __init__(self, paths, prepend=True):
        self.added = False
        self.paths = paths
        self.prepend = prepend

    def __enter__(self):
        if self.paths:
            if self.prepend:
                for path in self.paths:
                    sys.path.insert(0, path)
            else:
                sys.path.extend(self.paths)
            self.added = True

    def __exit__(self, type, value, traceback):
        if self.added:
            for path in self.paths:
                try:
                    sys.path.remove(path)
                except ValueError:
                    pass
        # Returning False causes any exceptions to be re-raised.
        return False


class ExtManager(object):
    """Extension manager for finchan.

    An finchan extension is an importable Python module that has
    a function with the signature::

        def load_finchan_ext(env):
            # Do setup

    This function is called after your extension is imported.
    \*args and \*\*kwargs is passed from configure file's `config.live_track_exts` or
    `config.backtrack_exts` 's extension module name section depend on the run mode.

    You can also optionally define an :func:`unload_finchan_ext()`
    function, which will be called if the user unloads the extension.

    You can put your extension modules anywhere you want, as long as
    they can be imported by Python's standard import mechanism.  However,
    to make it easy to write extensions, you can also put your extensions
    in a configured path `config.ext_paths`.
    This directory is added to ``sys.path`` automatically.
    """

    def __init__(self, env, ext_paths="", **kwargs):
        self.env = env
        self._ext_paths = ext_paths
        self._loaded_exts = OrderedDict()
        self._required_exts = []

    def add_requirement(self, ext_name):
        self._required_exts.append(ext_name)

    def load_exts(self, exts):
        """load exts for finchan:

        :param exts: exts dict, key is extension name, value is extension kwargs
        """
        logger.info("#Extm loading exts...")

        ext_groups = self.env.options.get("ext_groups", [])
        unloaded_exts = exts
        with add_to_syspath(self._ext_paths):
            while unloaded_exts:
                clean_exts = []
                for ext in unloaded_exts:
                    if ext in ext_groups:
                        clean_exts.extend(ext_groups[ext])
                    else:
                        clean_exts.append(ext)

                for ext_name in clean_exts:
                    logger.info("#Extm loading ext %s...", ext_name)
                    if ext_name in self._loaded_exts:
                        logger.warning("#Extm ext[%s] has been loaded: %s, skip...", ext_name, self._loaded_exts[ext_name])
                        continue
                    ext = import_module(ext_name)
                    if not hasattr(ext, "load_finchan_ext"):
                        logger.warning("#Extm Invalid ext[%s] for finchan: %s", ext_name, ext)
                        continue
                    try:
                        ext.load_finchan_ext(self.env)
                    except Exception as e:
                        logger.error("#Extm Load extensiong %s failed: %s", str(e))
                        continue
                    self._loaded_exts[ext_name] = ext
                    logger.info("#Extm ext[%s] loaded.", ext_name)

                unloaded_exts = []
                for ext in self._required_exts:
                    if ext not in self._loaded_exts:
                        unloaded_exts.append(ext)

    async def setup(self):
        """Initialize all extensions"""
        for ext_name in self._loaded_exts:
            ext = self._loaded_exts[ext_name]
            if hasattr(ext, "setup"):
                logger.info("#Extm setup for ext: %s", ext_name)
                await ext.setup(self.env)

    async def cleanup(self):
        """Cleanup all extensions"""
        for ext_name in self._loaded_exts:
            ext = self._loaded_exts[ext_name]
            if not hasattr(ext, "cleanup"):
                logger.info("#Extm cleanup for ext: %s", ext_name)
                await ext.cleanup(self.env)
