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
"""Event implentation"""
from enum import Enum
from datetime import datetime

from .env import env
from .utils import get_id_gen


class Event(object):
    """Event class

    :param name: name of the event
    :param dt: occur datetime
    :param expire: expire in second
    :param event_id: id of the event
    :param \*\*kwargs: special kwargs for the event, can get by kwargs attribute

    can compare less/greater than with other event object by time, equal by event id.
    """
    id_gen = get_id_gen(prefix='Event')

    def __init__(self, name, dt=None, expire=0, event_id=None, **kwargs):
        self._name = name
        self._event_id = event_id
        self._kwargs = kwargs
        self._expire = expire

        if dt:
            self._timestamp = dt.timestamp()
        else:
            self._timestamp = env.dispatcher.now.timestamp()
        if self._event_id is None:
            self._event_id = next(Event.id_gen)

    @property
    def id(self):
        """ID of the event"""
        return self._event_id

    @property
    def name(self):
        """Name of the event"""
        return self._name

    @property
    def timestamp(self):
        """Occur time of the event, in POSIX timestamp format"""
        return self._timestamp

    @property
    def expire(self):
        """expire expire in seconds after event occur time (timestamp attribute), 0 is no expire."""
        return self._expire

    @property
    def kwargs(self):
        """Parameters of the event, a `dict`"""
        return self._kwargs

    def __getattr__(self, name):
        return self._kwargs.get(name, None)

    def __eq__(self, other):
        return self.id == other.id

    def __ne__(self, other):
        return self.id != other.id

    def __lt__(self, other):
        if self.timestamp < other.timestamp:
            return True
        return False

    def __gt__(self, other):
        if self.timestamp > other.timestamp:
            return True
        return False

    def __repr__(self):
        return "<Event.%s:id=%s, time=%s, kwargs=%s>" % (self.name,
                                                         self.id,
                                                         datetime.fromtimestamp(self.timestamp),
                                                         self.kwargs)


class SysEvents(Enum):
    """system defined events

    enum of events that finchan system generate/reserved:

        * SYSTEM_STARTED = 'system_started'
    """
    SYSTEM_STARTED = 'system_event.system_started'

    def __repr__(self):
        return self.value

    def __str__(self):
        return self.value
