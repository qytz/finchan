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
"""EventSource Interface"""
import abc


class AbsEventSource(abc.ABC):
    """EventSource interface

    EventSource simulate some things in the real world to events,
    when event occurs it put the event into the event queue.

    main interface for dispatcher:

    :param start: start the event source.
    :param stop: stop the event source.
    :param gen_events: generate events and put them into event queue.
    """
    _name = None

    def __init__(self, *args, **kwargs):
        """init the event source"""
        pass

    @property
    def name(self):
        """Name of the event_source"""
        return self._name

    @abc.abstractmethod
    async def gen_events(self, event_queue, limit_dt=None):
        """Generate events for `Dispatcher`

        put all the generated/received events to event queue by call `Dispatcher.eq_put` ,

        event_queue: put all the generated event to the event_queue
        limit_dt: for backtest, gen events before the limit_dt

        for live track, the event source run in parallel mode, and should not return.

        for backtrack, the event source run in serial mode,
        and must return after put all events before limit_dt to event queue.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def start(self):
        """initialize the event_source, start generate/receive events"""
        raise NotImplementedError

    @abc.abstractmethod
    def stop(self):
        """stop the event_source, stop generate/receive events"""
        raise NotImplementedError
