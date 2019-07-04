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
"""Scheduler interface inspired by `schedule <https://github.com/dbader/schedule>`_

usage::

    async for dt in TimeScheduler(env).every(3).to(8).seconds():
        print("running periodly...")


"""
import logging
import random

from dateutil.parser import parse as parse_dt
from dateutil.relativedelta import relativedelta as timedelta

logger = logging.getLogger(__name__)


class TimeScheduler(object):
    """
    A Time Scheduler

    Every schedule runs at a given fixed time interval that is defined by:

    * a :meth:`time unit second <Scheduler.seconds>` or :meth:`time unit minite <Scheduler.minutes>` etc.
    * a quantity of `time units` defined by `step`

    A schedule is usually created and returned by :meth:`Scheduler.every` method which also defines its `interval` step

    unit types:

        * once
        * seconds
        * minutes
        * hours
        * days
        * weeks
        * months
        * years
    """

    unit_types = ["once", "seconds", "minutes", "hours", "days", "weeks", "months", "years"]

    def __init__(self, env):
        self.env = env

        self.unit = None
        self.run_dt = None
        self.next_run_dt = None
        self.min_step = self.max_step = 1
        self.bench_dt = parse_dt("1970-01-01 00:00:00")

    def bench(self, time_str: str):
        self.bench_dt = parse_dt(time_str)

    def every(self, step: int = 1):
        """
        create a new periodic scheduler.

        :param step: A quantity of a certain time unit
        :return: An unconfigured :class:`Scheduler <Scheduler>`
        """
        self.min_step = step
        return self

    def to(self, step: int):
        """
        make the schedule to run at an irregular (randomized) step.

        The schedule's interval will randomly vary from the value given
        to  `every <Scheduler.every>` to `step`.
        The range defined is inclusive on both ends.
        For example, `every(A).to(B).seconds` executes
        the job function every N seconds such that A <= N <= B.

        :param step: Maximum interval between randomized job runs
        :return: The invoked scheduler instance
        """
        self.max_step = step
        assert self.max_step >= self.min_step
        return self

    def seconds(self):
        """run in second steps

        :return: The job instance
        """
        self.unit = "seconds"
        return self

    def minutes(self):
        """run in minute steps

        :return: The job instance
        """
        self.unit = "minutes"
        return self

    def hours(self):
        """run in hour steps

        :return: The job instance
        """
        self.unit = "hours"
        return self

    def days(self):
        """run in day steps

        :return: The job instance
        """
        self.unit = "days"
        return self

    def weeks(self):
        """run in week steps

        :return: The job instance
        """
        self.unit = "weeks"
        return self

    def months(self):
        """run in month steps

        :return: The job instance
        """
        self.unit = "months"
        return self

    def years(self):
        """run in year steps

        :return: The job instance
        """
        self.unit = "years"
        return self

    def init(self):
        assert self.unit in Scheduler.unit_types
        replay_dict = {}
        if self.bench_dt.year < self.env.now.year:
            replay_dict["year"] = self.env.now.year

        if self.unit == "minutes":
            replay_dict["second"] = self.bench_dt.second
        if self.unit == "hours":
            replay_dict["minute"] = self.bench_dt.minute
            replay_dict["second"] = self.bench_dt.second
        if self.unit == "days":
            replay_dict["hour"] = self.bench_dt.hour
            replay_dict["minute"] = self.bench_dt.minute
            replay_dict["second"] = self.bench_dt.second
        if self.unit == "months":
            replay_dict["day"] = self.bench_dt.day
            replay_dict["hour"] = self.bench_dt.hour
            replay_dict["minute"] = self.bench_dt.minute
            replay_dict["second"] = self.bench_dt.second
        if self.unit == "years":
            replay_dict["month"] = self.bench_dt.month
            replay_dict["day"] = self.bench_dt.day
            replay_dict["hour"] = self.bench_dt.hour
            replay_dict["minute"] = self.bench_dt.minute
            replay_dict["second"] = self.bench_dt.second

        self.run_dt = self.next_run_dt = self.env.now.replace(**replay_dict)
        while self.next_run_dt < self.env.now:
            if self.max_step is not None:
                step = random.randint(self.min_step, self.max_step)
            else:
                step = self.min_step
            self.run_dt = self.next_run_dt
            self.next_run_dt = self.run_dt + timedelta(**{self.unit: step})
            logger.debug("#Scheduler last run:%s next run:%s", self.run_dt, self.next_run_dt)
        return self

    def __aiter__(self):
        self.init()
        return self

    async def __anext__(self):
        sleep_seconds = (self.next_run_dt - self.env.now).total_seconds()
        logger.debug("#Scheduler anext, now:%s next_run_dt:%s", self.env.now, self.next_run_dt)
        await self.env.dispatcher.sleep(sleep_seconds)
        if self.max_step is not None:
            step = random.randint(self.min_step, self.max_step)
        else:
            step = self.min_step
        self.run_dt = self.next_run_dt
        self.next_run_dt = self.run_dt + timedelta(**{self.unit: step})
        return self.run_dt

    async def __wait__(self):
        return self
