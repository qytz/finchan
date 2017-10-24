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
"""Event Dispatcher

get events from event source and dispatch evnets to the subscriber.
"""
import os
import abc
import time
import signal
import asyncio
import logging
import threading
from queue import Queue, PriorityQueue, Empty
from datetime import datetime
from collections import defaultdict

from finchan.event import Event
from finchan.interface.event_source import AbsEventSource


logger = logging.getLogger(__name__)


class BaseDispatcher(abc.ABC):
    """Event dispatcher abstract clsss.

    methods subclass should implement:

        * setup: need to start all the event sources and can also do other setup things.
        * cleanup: stop all the evnent source and do other cleanup things.
        * get_next_event: return the next event to dispath.


    :param eventq: queue to r/s event
    :param end_dt: dispatch end time
    """
    def __init__(self, **kwargs):
        self._will_stop = False
        self._event_sources = []
        self._end_dt = kwargs.get('end_dt')
        self._eventq = kwargs.get('eventq')
        self._event_subscribes = defaultdict(list)

        self._start_dt = datetime.now()
        self._event_timestamp = self._event_process_timestamp = self._start_dt.timestamp()

        # signal: ctrl_c/ctrl_\ quit
        signal.signal(signal.SIGINT, self.quit_handler)
        # signal.signal(signal.SIGQUIT, self.quit_handler)

    @property
    def now(self):
        """datetime of current"""
        return datetime.now()

    def quit_handler(self, signum, frame):
        """quit signal handler, callbacks for signal: ctrl\_c/ctrl\_\\"""
        self._will_stop = True
        logger.info('#Dispatcher get signal: %s system will exit.', signum)

    def register_event_source(self, event_source):
        """register new event source

        :param event_source: an `AbsEventSource` subclass instance object
        :return: True if register succeed else False.
        """
        if not isinstance(event_source, AbsEventSource):
            logger.warning('#Dispatcher Trying to add invalid EventSource falied: '
                           'EventSource must be isinstance of AbsEventSource')
            return False
        self._event_sources.append(event_source)
        logger.info('#Dispatcher New event source has been registered: %s.', event_source)
        return True

    def deregister_event_source(self, event_source):
        """deregister an event source

        :param event_source: an `AbsEventSource` subclass instance object
        :return: True if deregister succeed, else False.
        """
        if not isinstance(event_source, AbsEventSource):
            logger.warning('#Dispatcher Trying to remove invalid EventSource falied: '
                           'EventSource must be isinstance of AbsEventSource')
            return False
        self._event_sources.remove(event_source)
        logger.info('#Dispatcher Event source %s has been deregistered.', event_source)
        return True

    def subscribe(self, name, callback, prepend=False):
        """subscribe an event

        when the event occurs, the callback will be called.

        :param name: name of the event
        :param callback: the callback func will be called
        :param prepend: add to the head of callbacks if `True` , else add to the end.
        :return: True if subscribe succeed, else False.
        """
        if not callable(callback):
            logger.warning(
                '#Dispatcher Failed to subscribe event: callback callable must be callable.')
            return False
        if not isinstance(name, str):
            logger.warning('#Dispatcher Failed to subscribe event: event name must be str.')
            return False
        self._event_subscribes.setdefault(name, [])
        if prepend:
            self._event_subscribes[name].insert(0, callback)
        else:
            self._event_subscribes[name].append(callback)
        logger.info('#Dispatcher New callback: %s for event %s has been added.', callback, name)
        return True

    def unsubscribe(self, name, callback):
        """unsubscribe an event

        :param name: name of the event
        :param callback: the callback func will be called
        :return: True if unsubscribe succeed, else False.
        """
        if not callable(callback):
            logger.warning(
                '#Dispatcher Failed to subscribe event: callback callable must be callable.')
            return False
        if not isinstance(name, str):
            logger.warning('#Dispatcher Failed to subscribe event: event name must be str.')
            return False
        self._event_subscribes.setdefault(name, [])
        self._event_subscribes[name].remove(callback)
        logger.info('#Dispatcher Callback: %s for event %s has been removed.', callback, name)
        return True

    # --- event_queue op ---
    def eq_put(self, *events):
        """put an event into event_queue, should not be blocked"""
        for event in events:
            if not isinstance(event, Event):
                logger.warning(
                    '#Dispatcher Put event failed: event must be instance of Event, %s', event)
                continue
            self._eventq.put(event)

    def eq_get(self, timeout=None):
        """Remove and return an event from the queue

        May be blcoked if the event_queue is empty.
        """
        event = self._eventq.get(timeout=timeout)
        if event:
            self._eventq.task_done()
        return event

    def eq_get_nowait(self):
        """Remove and return an event from the queue

        return None if the event_queue is empty.
        """
        event = self._eventq.get_nowait()
        if event:
            self._eventq.task_done()
        return event

    def eq_size(self):
        """count of event in the queue"""
        return self._eventq.qsize()

    def es_size(self):
        """count of `EventSource` that registered"""
        return len(self._event_sources)

    def cb_size(self, event):
        """count of callbcaks of the event"""
        return len(self._event_subscribes[event])

    def start_event_sources(self):
        """start the event sources"""
        for event_source in self._event_sources:
            try:
                logger.info('#Dispatcher starting event source %s...', event_source)
                event_source.start()
            except Exception as e:
                logger.warning('#Dispatcher Start event source %s failed: %s', event_source.name, e)

    def stop_event_sources(self):
        """stop the event sources"""
        for event_source in self._event_sources:
            try:
                logger.info('#Dispatcher stoping event source %s...', event_source)
                event_source.stop()
                logger.debug('#Dispatcher event source %s stopped', event_source)
            except Exception as e:
                logger.warning('#Dispatcher Stop event source %s failed: %s', event_source.name, e)

    def get_next_event(self):
        """return next event to process"""
        raise NotImplementedError

    def setup(self):
        """setup before dispatch,
        need to start all the event sources and can also do other setup things."""
        self.start_event_sources()

    def cleanup(self):
        """cleanup the dispatcher,
        stop all the evnent source and do other cleanup things.
        """
        self.stop_event_sources()

    def dispatch(self):
        """dispatch the event loop to run."""
        if not self._event_sources:
            self._will_stop = True
            logger.warning('#Dispatcher No EventSource registered, system will exit directly.')
            return None

        self.setup()
        last_event = None
        while True:
            event = self.get_next_event()
            if not event:
                logger.info('#Dispatcher get_next_event return None, exit.')
                break
            if event.expire != 0 and self.now.timestamp() > event.timestamp + event.expire:
                logger.warning(
                    '#Dispatcher Event %s process too slow, currend time: %s, skipped event: %s.',
                    last_event,
                    self.now,
                    event)
                self._event_process_timestamp = time.time()
                continue
            self._event_timestamp = event.timestamp
            self._event_process_timestamp = time.time()
            logger.debug('#Dispatcher Start process event: %s', event)
            for call_func in self._event_subscribes[event.name]:
                call_func(event)
            last_event = event
            if self.now >= self._end_dt:
                logger.info('#Dispatcher Run out of time, dispatch finish.')
                break
            if self._will_stop:
                break

        logger.info('#Dispatcher loop exit.')
        self._will_stop = True
        self.cleanup()

    async def _wrap_coroutine(self, coroutine, *args, **kwargs):
        """wrap coroutine, catch exceptions"""
        try:
            await coroutine(*args, **kwargs)
        except Exception as e:
            logger.error('coroutine: %s exception: %s', coroutine, e)


class BackTrackDispatcher(BaseDispatcher):
    """BackTrackDispatcher

    Simulately dispatch history events.
    it generate events when calling `get_next_event` and the event queue is empty.

    All the event generate, event dispatch,
    event callbacks are run in one process and thread serialy.

    :param start_dt: dispatch start time
    :param end_dt: dispatch end time
    :param time_step: time step for backtrack dispatch
    :param trace_process_time: pass
    """
    def __init__(self, **kwargs):
        eventq = PriorityQueue()
        super().__init__(eventq=eventq, **kwargs)

        self._start_dt = kwargs.get('start_dt')
        self._time_step = kwargs.get('time_step', 86400)
        self._trace_process_time = kwargs.get('trace_process_time', False)

        self._event_timestamp = self._start_dt.timestamp()
        self._event_process_timestamp = time.time()
        self._gen_dt = self.now

    @property
    def now(self):
        """datetime of current logic time"""
        if not self._trace_process_time:
            return datetime.fromtimestamp(self._event_timestamp)

        elasped_time = time.time() - self._event_process_timestamp
        return datetime.fromtimestamp(self._event_timestamp + elasped_time)

    def gen_events(self):
        """generate events from event sources."""
        futures = []
        limit_dt = datetime.fromtimestamp(self._gen_dt.timestamp() + self._time_step)
        if limit_dt > self._end_dt:
            limit_dt = self._end_dt
        for event_source in self._event_sources:
            futures.append(self._wrap_coroutine(event_source.gen_events, self._eventq, limit_dt))

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError as e:
            asyncio.set_event_loop(asyncio.new_event_loop())
            loop = asyncio.get_event_loop()
        loop.run_until_complete(asyncio.gather(*futures, return_exceptions=True))
        logger.debug('#Dispatcher Forward backtrack time from %s to %s...', self._gen_dt, limit_dt)
        self._gen_dt = limit_dt

    def get_next_event(self):
        """return next event to process"""
        if self.eq_size() == 0:
            self.gen_events()
            if self.eq_size() == 0:
                return None
        return self.eq_get()


class LiveDispatcher(BaseDispatcher):
    """LiveDispatcher

    Dispatch realtime events.
    all the event sources are run in one dedicated thread in `coroutine` mode.
    the event sources generate events and put them into event queue,
    the main thread get events from event queue and dispath them.


    :param stop_check_interval: stop check interval
    """
    def __init__(self, **kwargs):
        eventq = Queue()
        # the thread should check exit after main thread call join, other will run in deadlock.
        self._thread_exit = False
        self._event_source_thread = None
        # never stop by runout time.
        end_dt = datetime.strptime('9999-12-31', '%Y-%m-%d')
        super().__init__(eventq=eventq, end_dt=end_dt, **kwargs)
        self._stop_check_interval = kwargs.get('stop_check_interval', 5)

    async def stop_check(self):
        """check if the dispatcher should stop, runs in the event source thread."""
        while True:
            if self._thread_exit:
                break
            await asyncio.sleep(self._stop_check_interval)
        loop = asyncio.get_event_loop()
        loop.stop()

    def gen_events(self):
        """generate events from event sources."""
        asyncio.set_event_loop(asyncio.new_event_loop())
        loop = asyncio.get_event_loop()
        self.start_event_sources()
        while True:
            if self._thread_exit:
                break
            futures = [self.stop_check()]
            for event_source in self._event_sources:
                futures.append(event_source.gen_events(self._eventq))
                # futures.append(self._wrap_coroutine(event_source.gen_events, self._eventq))
            if not futures:
                logger.warning('#Dispatcher No event source futures found, '
                               'EventSourceManager thread exiting.')
                break
            try:
                loop.run_until_complete(asyncio.gather(*futures, return_exceptions=True))
            except RuntimeError as e:
                logger.error('#Dispatcher run exception: %s', e)
        logger.debug('#Dispatcher gen event thread exit.')
        return None

    def get_next_event(self):
        """get next event will in the queue to process

        :return: next event to process
        """
        while True:
            try:
                return self.eq_get(timeout=self._stop_check_interval)
            except Empty:
                if self._will_stop:
                    return None

    def setup(self):
        """setup before dispatch, should start all event sources"""
        self._event_source_thread = threading.Thread(
            target=self.gen_events, name='EventSourceManager')
        self._event_source_thread.start()

    def cleanup(self):
        """cleanup the dispatcher"""
        super().cleanup()
        self._thread_exit = True
        if self._event_source_thread:
            self._event_source_thread.join()
