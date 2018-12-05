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
import time
import signal
import asyncio
import logging
import functools
from asyncio import Queue, PriorityQueue, QueueEmpty
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from datetime import datetime, timedelta
from collections import defaultdict

from .event import Event, SysEvents
from finchan.interface.event_source import AbsEventSource


logger = logging.getLogger(__name__)


class LiveTrackDispatcher(object):
    """
    Dispatcher that dispatch real time events.
    the event sources generate events and put them into event queue,
    the main thread get events from event queue and dispatch them.

    :param env: global environment
    """
    def __init__(self, env):
        self.env = env
        self._event_sources = {}
        self._es_tasks = {}
        self._event_subscribes = defaultdict(list)

        if env.run_mode == "live_track":
            conf = env.options.get("dispatcher.live_track")
            queue_size = conf.get("equeue_size", 0)
            self._eventq = Queue()
        else:
            conf = env.options.get("dispatcher.backtrack")
            queue_size = conf.get("equeue_size", 0)
            self._eventq = PriorityQueue()

        self._time_step = conf.get("time_step", 86400)  # default to one day
        self._trace_process_time = conf.get("trace_process_time", False)
        self._start_dt = conf.get("start_dt", datetime.now())
        self._end_dt = conf.get("end_dt", datetime.strptime("9999-12-31", "%Y-%m-%d"))

        self._wait_subscribers = conf.get("wait_subscribers", True)
        self._check_cycle = 0
        self._check_es_freq = conf.get("check_event_source_cycles", 1)

        self._thread_executor = None
        self._process_executor = None
        self._max_thread_workers = conf.get("thread_workers", None)
        self._max_process_workers = conf.get("process_workers", None)

        self._gen_dt = self._start_dt
        self._elasped_mark_time = time.time()
        self._event_occur_ts = self._event_dispatch_ts = self._start_dt.timestamp()

    @property
    def now(self):
        """datetime of current logic time"""
        return datetime.now()

    def quit_handler(self, signame):
        """quit signal handler, callbacks for signal: ctrl\_c/ctrl\_\\"""
        self.run_async_task(self.cleanup())

    def register_signals(self, loop=None):
        """register signals for the loop"""
        loop = loop or asyncio.get_running_loop()
        if not loop:
            return False
        # for signame in {"SIGINT", "SIGTERM"}:
        for signame in {"SIGINT"}:
            loop.add_signal_handler(
                getattr(signal, signame), functools.partial(self.quit_handler, signame)
            )

    def register_event_source(self, event_source):
        """register new event source

        :param event_source: an `AbsEventSource` subclass instance object
        :return: True if register succeed else False.
        """
        if not isinstance(event_source, AbsEventSource):
            logger.error(
                "#Dispatcher Add EventSource<%s> falied: "
                "EventSource must be isinstance of AbsEventSource",
                event_source,
            )
            return False
        self._event_sources[event_source.name] = event_source
        logger.info("#Dispatcher New EventSource<%s> has been added.", event_source)
        return True

    def deregister_event_source(self, event_source):
        """deregister an event source

        :param event_source: an `AbsEventSource` subclass instance object
        :return: True if deregister succeed, else False.
        """
        if not isinstance(event_source, AbsEventSource):
            logger.warning(
                "#Dispatcher Trying to remove EventSource<%s> falied: parameter invalid",
                event_source,
            )
            return False
        es_name = event_source.name
        if es_name not in self._event_sources:
            logger.warning(
                "#Dispatcher Trying to remove EventSource<%s> falied: not registered", event_source
            )
            return False

        if es_name in self._es_tasks:
            task = self._es_tasks.pop(es_name)
            try:
                task.cancel()
            except Exception:
                pass
            event_source.stop()
        del self._event_sources[es_name]
        logger.info("#Dispatcher Eventsource<%s> has been deregistered.", event_source)
        return True

    def subscribe(self, event_name, callback, prepend=False):
        """subscribe an event

        when the event occurs, the callback will be called.

        :param event_name: name of the event
        :param callback: the callback func will be called
        :param prepend: add to the head of callbacks if `True` , else add to the end.
        :return: True if subscribe succeed, else False.
        """
        if not isinstance(event_name, str):
            logger.error("#Dispatcher Failed to subscribe event: event name must be str.")
            return False
        if not callable(callback):
            logger.error(
                "#Dispatcher Failed to subscribe event<%s>: callback<%s> is not callable.",
                event_name,
                callback,
            )
            return False
        if prepend:
            self._event_subscribes[event_name].insert(0, callback)
        else:
            self._event_subscribes[event_name].append(callback)
        logger.info(
            "#Dispatcher New callback: %s for event %s has been added.", callback, event_name
        )
        return True

    def unsubscribe(self, event_name, callback):
        """unsubscribe an event

        :param event_name: name of the event
        :param callback: the callback func will be called
        :return: True if unsubscribe succeed, else False.
        """
        if not isinstance(event_name, str):
            logger.error(
                "#Dispatcher Failed to unsubscribe event<%s>: event name must be str.", event_name
            )
            return False
        try:
            self._event_subscribes[event_name].remove(callback)
        except ValueError:
            logger.error(
                "#Dispatcher Failed to unsubscribe event<%s>: %s not subscribed.",
                event_name,
                callback,
            )

        logger.info(
            "#Dispatcher Callback<%s> for Event<%s> has been unsubscribed.", callback, event_name
        )
        return True

    def get_es_count(self):
        """count of EventSource"""
        return len(self._event_sources)

    def get_active_es_count(self):
        """count of active EventSource"""
        return len(self._event_sources)

    def get_pending_events_count(self):
        """count of pending Event"""
        return self._eventq.qsize()

    def get_subscriber_count(self, event_name):
        """count of subscriber of an Event"""
        return len(self._event_subscribes[event_name])

    @staticmethod
    def run_async_task(cor):
        """schedule the coroutine to run"""
        try:
            return asyncio.create_task(cor)
        except AttributeError:
            return asyncio.ensure_future(cor)

    # --- async funcs ---
    async def setup(self):
        """setup before dispatch"""
        self.register_signals(asyncio.get_running_loop())
        await self.put_event(Event(self.env, SysEvents.SYSTEM_STARTED))

    async def cleanup(self):
        """stop the dispatcher, do the cleanup stuffs"""
        # system is exiting
        quit_event = Event(self.env, SysEvents.SYSTEM_EXITING)
        await self.call_subscribers(quit_event)
        logger.info("#Dispatcher loop exit.")

        # self.stop_event_sources()
        try:  # Python <3.7 has no the method
            for task in asyncio.all_tasks():
                task.cancel()
        except AttributeError:
            for task in asyncio.Task.all_tasks():
                task.cancel()

        if self._thread_executor:
            self._thread_executor.shutdown(wait=True)
        if self._process_executor:
            self._process_executor.shutdown(wait=True)

        loop = asyncio.get_running_loop()
        if loop:
            loop.stop()

    async def run_in_executor(self, func, run_mode="thread", *args, **kwargs):
        """run synchronous func in the executor"""
        executor = None
        if run_mode == "process":
            max_workers = self._max_process_workers
            if not self._process_executor:
                self._process_executor = ProcessPoolExecutor(max_workers=max_workers)
            executor = self._process_executor
        elif run_mode == "process":
            max_workers = self._max_thread_workers
            if not self._thread_executor:
                self._thread_executor = ThreadPoolExecutor(max_workers=max_workers)
            executor = self._thread_executor
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(executor, functools.partial(func, *args, **kwargs))

    async def put_event(self, event):
        """put an event into event_queue, may be blocked"""
        if not isinstance(event, Event):
            logger.warning(
                "#Dispatcher Put Event<%s> failed: event must be instance of Event.", event
            )
            return False
        return await self._eventq.put(event)

    async def get_event(self):
        """get next event from event_queue, my be blocked"""
        return await self._eventq.get()

    async def call_subscribers(self, event):
        """call the subscribers of the event"""
        if not self._event_subscribes[event.name]:
            return
        tasks = []
        for call_func in self._event_subscribes[event.name]:
            tasks.append(self.run_async_task(call_func(event)))

        # await asyncio.gather(*tasks, return_exceptions=True)
        for task in asyncio.as_completed(tasks):
            try:
                await task
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error("#Dispatcher callback for %s raise an exception: %s", event, e)
        return True

    async def check_event_sources(self):
        """check the status of EventSource and start new EventSources."""
        self._check_cycle -= 1
        if self._check_cycle > 0:
            return
        self._check_cycle = self._check_es_freq
        for es_name in self._event_sources:
            if es_name not in self._es_tasks:
                logger.info("#Dispatcher Trying to start EventSource<%s>", es_name)
                es = self._event_sources[es_name]
                try:
                    es.start()
                except Exception as e:
                    logger.error("#Dispatcher Start EventSource<%s> failed: %s", es_name, e)
                else:
                    self._es_tasks[es.name] = self.run_async_task(es.gen_events())
                continue

            task = self._es_tasks[es_name]
            if task.done():
                logger.warning("#Dispatcher EventSource<%s> gen_events is done.", es_name)
                try:
                    task.result()
                except Exception as e:
                    logger.warning(
                        "#Dispatcher EventSource<%s> is done by Exception<%s>, try to restart it.",
                        es_name,
                        str(e),
                    )
                    es = self._event_sources[es_name]
                    self._es_tasks[es_name] = self.run_async_task(es.gen_events())
        return True

    async def loop(self):
        """dispatch the event loop to run."""
        # system initialized first
        await self.setup()
        last_event = None
        while True:
            await self.check_event_sources()
            event = await self.get_event()
            self._elasped_mark_time = time.time()
            if not event:
                logger.info("#Dispatcher get_event return None, exit.")
                break
            if event.expire != 0 and self.now.timestamp() > event.timestamp + event.expire:
                logger.warning(
                    "#Dispatcher event %s expired: %s, now: %s, previous event: %s.",
                    event,
                    self.now,
                    last_event,
                )
                self._event_dispatch_ts = self.now.timestamp()
                continue
            self._event_occur_ts = event.timestamp
            self._event_dispatch_ts = self.now.timestamp()
            logger.info(
                "#Dispatcher Start process event: %s, occur at: %s dispatch at: %s",
                event,
                self._event_occur_ts,
                self._event_dispatch_ts,
            )
            if self._wait_subscribers:
                await self.call_subscribers(event)
            else:
                self.run_async_task(self.call_subscribers(event))
            last_event = event
            if self.now >= self._end_dt:
                logger.info("#Dispatcher Run out of time, dispatch finish.")
                break
        await self.cleanup()

    def run(self):
        """main entrance"""
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(self.loop())
        except asyncio.CancelledError:
            pass


class BackTrackDispatcher(LiveTrackDispatcher):
    """
    Dispatcher that dispatch backtrack events.
    the event sources generate events and put them into event queue,
    the main thread get events from event queue and dispatch them.

    :param env: global envirument
    """
    @property
    def now(self):
        """datetime of current logic time"""
        if not self._trace_process_time:
            return datetime.fromtimestamp(self._event_dispatch_ts)

        elasped_time = time.time() - self._elasped_mark_time
        return datetime.fromtimestamp(self._event_dispatch_ts + elasped_time)

    async def get_event(self):
        """return next event to process"""
        while True:
            if not self._eventq.empty() or self._gen_dt >= self._end_dt:
                break
            limit_dt = self._gen_dt + timedelta(seconds=self._time_step)
            if limit_dt > self._end_dt:
                limit_dt = self._end_dt
            wait_tasks = []
            for es_name, es in self._event_sources.items():
                wait_tasks.append(es.gen_events(limit_dt))
            await asyncio.gather(*wait_tasks, return_exceptions=True)
            self._gen_dt = limit_dt

        try:
            return self._eventq.get_nowait()
        except QueueEmpty:
            return None

    async def check_event_sources(self):
        """generate events from event sources."""
        pass


def get_dispatcher(env):
    if env.run_mode == "backtrack":
        return BackTrackDispatcher(env)
    return LiveTrackDispatcher(env)
