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
import asyncio
import functools
import logging
import signal
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def task_done(task):
    # logger.info("task %s is done: %s", task, task.result())
    try:
        task.result()
    except asyncio.CancelledError:
        logger.error("task[%s] has been canceled", task.task_name)
    except Exception as e:
        logger.error("task[%s] raise an exception:%s", task.task_name, e)


class Dispatcher:
    pass


class LiveTrackDispatcher(Dispatcher):
    """
    Dispatcher that dispatch real time events.
    the event sources generate events and put them into event queue,
    the main thread get events from event queue and dispatch them.

    :param env: global environment
    """

    def __init__(self, env):
        self.env = env

        conf = env.options.get("dispatcher")
        self._trace_process_time = conf.get("trace_process_time", False)
        self._start_dt = conf.get("start_dt", datetime.now())
        self._end_dt = conf.get("end_dt", datetime.strptime("9999-12-31", "%Y-%m-%d"))
        self._limit_time = conf.get("limit_time", True)

        self._thread_executor = None
        self._process_executor = None
        self._max_thread_workers = conf.get("thread_workers", None)

        self._main_task = None
        self._quit_event = None

    @property
    def now(self):
        """datetime of current logic time"""
        return datetime.now()

    def quit_handler(self, signame):
        """quit signal handler, callbacks for signal: ctrl_c/ctrl_\\."""
        self._quit_event.set()

    def register_signals(self, loop=None):
        """register signals for the loop"""
        loop = loop or asyncio.get_running_loop()
        if not loop:
            return False
        # for signame in {"SIGINT", "SIGTERM"}:
        for signame in {"SIGINT"}:
            loop.add_signal_handler(getattr(signal, signame), functools.partial(self.quit_handler, signame))

    @staticmethod
    def schedule_task(cor):
        """schedule the coroutine to run"""
        try:
            task = asyncio.create_task(cor)
        except AttributeError:
            task = asyncio.ensure_future(cor)
        task.task_name = repr(cor)
        task.add_done_callback(task_done)
        return task

    @staticmethod
    def all_tasks():
        """schedule the coroutine to run"""
        try:  # Python <3.7 has no the method
            return asyncio.all_tasks()
        except AttributeError:
            return asyncio.Task.all_tasks()

    @staticmethod
    def current_task():
        """get current active task"""
        try:  # Python <3.7 has no the method
            return asyncio.current_task()
        except AttributeError:
            return asyncio.Task.current_task()

    # --- async funcs ---
    async def quit_checker(self)->None:
        while True:
            await self.sleep(1)
            if len(self.all_tasks()) == 2:
                logger.debug("only one task")
                break
            if self.now >= self._end_dt:
                logger.debug("reach endtime")
                break
        self._quit_event.set()

    async def quit(self) -> None:
        """stop the dispatcher, do the cleanup stuffs"""
        await self._quit_event.wait()

        # system is exiting
        logger.info("#Dispatcher stop running.")
        # call extensions' cleanup
        await self.env.ext_manager.cleanup()

        # shutdown all executors
        if self._thread_executor:
            self._thread_executor.shutdown(wait=True)
        if self._process_executor:
            self._process_executor.shutdown(wait=True)

        # cancel all tasks
        for task in self.all_tasks():
            if task == asyncio.current_task() or task == self._main_task:
                continue
            task.cancel()

        for task in self.all_tasks():
            # no need to await current task
            if task == asyncio.current_task() or task == self._main_task:
                continue
            try:
                await task
            except asyncio.CancelledError:
                pass

        # loop = asyncio.get_running_loop()
        # if loop:
        #     loop.stop()

    async def run_in_thread(self, func, run_mode="thread", *args, **kwargs):
        """run synchronous func in the executor"""
        if not self._thread_executor:
            self._thread_executor = ThreadPoolExecutor(max_workers=self._max_thread_workers)
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(self._thread_executor, functools.partial(func, *args, **kwargs))

    async def run_in_process(self, func, *args, **kwargs):
        if not self._process_executor:
            self._process_executor = ProcessPoolExecutor()
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(self._process_executor, functools.partial(func, *args, **kwargs))

    async def sleep(self, delay: float) -> None:
        return await asyncio.sleep(delay)

    async def run(self):
        """dispatch the event loop to run."""
        self._main_task = self.current_task()
        self._quit_event = asyncio.Event()
        self.register_signals(asyncio.get_running_loop())
        self.schedule_task(self.quit_checker())
        self.schedule_task(self.env.ext_manager.setup())
        await self.quit()


class BackTrackDispatcher(LiveTrackDispatcher):
    """
    Dispatcher that dispatch backtrack events.
    the event sources generate events and put them into event queue,
    the main thread get events from event queue and dispatch them.

    :param env: global envirument
    """

    def __init__(self, env):
        super().__init__(env)
        self.sleep_queue = []
        self._now = self._start_dt
        self._need_forword = self._now < datetime.now()

    @property
    def now(self):
        """datetime of current logic time"""
        if self._limit_time:
            if not self._need_forword:
                return datetime.now()

            if self._now >= datetime.now():
                self._need_forword = False
                return datetime.now()
            else:
                return self._now
        else:
            return self._now

    async def sleep(self, delay: float) -> None:
        self.sleep_queue.append(delay)
        self.sleep_queue.sort()
        while True:
            while len(self.all_tasks()) > 2:
                logger.debug("all_tasks:%s", self.all_tasks())
                await asyncio.sleep(0.1)

            try:
                elasped = self.sleep_queue.pop(0)
            except IndexError:
                return
            logger.info("elasped:%s delay:%s", elasped, delay)
            self._now += timedelta(seconds=elasped)
            if elasped == delay:
                return

    async def get_events(self):
        pass

    async def foward(self):
        pass

    async def run(self):
        """dispatch the event loop to run."""
        self._main_task = self.current_task()
        self._quit_event = asyncio.Event()
        self.register_signals(asyncio.get_running_loop())
        self.schedule_task(self.quit_checker())
        self.schedule_task(self.env.ext_manager.setup())
        while True:
            pass
        await self.quit()


def get_dispatcher(env):
    if env.run_mode == "backtrack":
        return BackTrackDispatcher(env)
    return LiveTrackDispatcher(env)
