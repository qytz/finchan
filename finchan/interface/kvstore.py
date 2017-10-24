# -*- coding: utf-8 -*-
# This file is part of finchan.

# Copyright (C) 2017-Present qytz <hhhhhf@foxmail.com>
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
"""kvstore Interface, inspired by redis-py."""
import abc


class AbsKvStore(abc.ABC):
    """KV store interface"""
    _name = None

    def __init__(self, *args, **kwargs):
        """init the kvstore connection"""
        pass

    # --- kv ---
    def set(self, name, value):
        """Set the value at key name to value."""
        raise NotImplementedError

    def get(self, name):
        """Return the value at key name, or None if the key doesn’t exist."""
        raise NotImplementedError

    def mset(self, *args, **kwargs):
        """Sets key/values based on a mapping.
        Mapping can be supplied as a single dictionary argument or as kwargs."""
        raise NotImplementedError

    def mget(self, keys, *args):
        """Returns a list of values ordered identically to keys."""
        raise NotImplementedError

    def setnx(self, name, value):
        """Set the value of key name to value if key doesn’t exist."""
        raise NotImplementedError

    def delete(self, name):
        """Delete the key and its value."""
        raise NotImplementedError

    # --- hashmap ---
    def hset(self, name, key, value):
        """Set key to value within hash name.

        Returns 1 if HSET created a new field, otherwise 0."""
        raise NotImplementedError

    def hget(self, name, key):
        """Return the value of ``key`` within the hash ``name``."""
        raise NotImplementedError

    def hmset(self, name, mapping):
        """Set key to value within hash ``name`` for each corresponding
        key and value from the ``mapping`` dict."""
        raise NotImplementedError

    def hmget(self, name, keys, *args):
        """Returns a list of values ordered identically to ``keys``."""
        raise NotImplementedError

    def hgetall(self, name):
        """Return a Python dict of the hash's name/value pairs."""
        raise NotImplementedError

    def hsetnx(self, name, key, value):
        """Set key to value within hash name if key does not exist.

        Returns 1 if HSETNX created a field, otherwise 0."""
        raise NotImplementedError

    def hdel(self, name, *keys):
        """Delete ``keys`` from hash ``name``."""
        raise NotImplementedError

    def hexists(self, name, key):
        """Returns a boolean indicating if ``key`` exists within hash ``name``."""
        raise NotImplementedError

    def hkeys(self, name):
        """Return the list of keys within hash ``name``."""
        raise NotImplementedError

    def hvals(self, name):
        """Return the list of values within hash ``name``."""
        raise NotImplementedError

    def hlen(self, name):
        """Return the number of elements in hash ``name``."""
        raise NotImplementedError

    # --- list ---
    def lpop(self, name):
        """Remove and return the first item of the list ``name``."""
        raise NotImplementedError

    def lpush(self, name, value):
        """Push ``values`` onto the head of the list ``name``."""
        raise NotImplementedError

    def rpop(self, name):
        """Remove and return the last item of the list ``name``."""
        raise NotImplementedError

    def rpush(self, name, *value):
        """Push ``values`` onto the tail of the list ``name``."""
        raise NotImplementedError

    def lset(self, name, index, value):
        """Set ``position`` of list ``name`` to ``value``."""
        raise NotImplementedError

    def lrange(self, name, start, end):
        """Return a slice of the list ``name`` between
        position ``start`` and ``end``.

        ``start`` and ``end`` can be negative numbers just like
        Python slicing notation."""
        raise NotImplementedError

    def ltrim(self, name, start, end):
        """Trim the list ``name``, removing all values not within the slice
        between ``start`` and ``end``.

        ``start`` and ``end`` can be negative numbers just like
        Python slicing notation."""
        raise NotImplementedError

    def llen(self, name):
        """Return the length of the list ``name``"""
        raise NotImplementedError
