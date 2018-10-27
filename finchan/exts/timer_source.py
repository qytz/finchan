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
"""Timer event source, interface inspired by `schedule <https://github.com/dbader/schedule>`_

usage::

    def setup(env)
        scheduler = env.get_ext_obj('finchan.exts.timer_source')
        scheduler.run_every(3).to(5).minutes().do(timer_call)
        scheduler.run_every(1).days.offset('09:31').tag('daily_task').do(timer_call)
        # runs on every two weeks' friday 09:31
        scheduler.run_every(2).weeks.offset('friday 09:31').tag('daily_task').do(timer_call)
        # runs on every month's 09 day 09:31
        scheduler.run_every(1).months.offset('09 09:31').tag('daily_task').do(timer_call)


    def clean(env)
        scheduler = env.get_ext_obj('finchan.exts.timer_source')
        scheduler.cancel_all_jobs()

"""
import random
import asyncio
import logging
import collections
from datetime import datetime
from dateutil.parser import parse as parse_dt
from dateutil.relativedelta import relativedelta

from finchan.event import Event
from finchan.utils import get_id_gen
from finchan.interface.event_source import AbsEventSource


# name of the extension
ext_name = 'finchan.exts.timer_source'
# required extension
required_exts = []

logger = logging.getLogger(__name__)


def event_callback(event):
    """call timer func in event callback"""
    func = event.kwargs['func']
    return func(event.env, *event.kwargs['args'], **event.kwargs['kwargs'])


class JobMananger(object):
    """
    Objects instantiated by the :class:`JobMananger <JobMananger>` are
    factories to create jobs, keep record of scheduled jobs and
    handle their execution.

    TODO: schedule with asyncio.sleep(idle_seconds) and loop.create_task and task.cancel.
    """
    def __init__(self, env):
        self.env = env
        self.jobs = []
        self.curr_job = None

    def run_once(self, dt):
        """Schedule a new job that only runs once time.

        :param dt: the `datetime <datetime.datetime>` object that the job will run.
        :return: An unconfigured :class:`Job <Job>`
        """
        job = Job(step='once', next_run=dt, job_manager=self, unit='once')
        return job

    def run_every(self, step=1):
        """
        Schedule a new periodic job.

        :param step: A quantity of a certain time unit
        :return: An unconfigured :class:`Job <Job>`
        """
        job = Job(step=step, job_manager=self)
        return job

    def add_job(self, job):
        """Add a new job to the `JobMananger`"""
        self.jobs.append(job)

    def cancel(self, job):
        """cancel a job's schedule"""
        try:
            self.jobs.remove(job)
        except ValueError:
            pass

    def clear(self, tag=None):
        """
        Deletes scheduled jobs marked with the given tag, or all jobs
        if tag is `None`.

        :param tag: An identifier used to identify a subset of
                    jobs to delete
        """
        if tag is None:
            del self.jobs[:]
        else:
            self.jobs[:] = (job for job in self.jobs if tag not in job.tags)

    def cancel_all_jobs(self):
        """cancel all jobs"""
        self.jobs.clear()

    def get_next_job(self):
        """Get next job to run"""
        if not self.jobs:
            return None
        return min(self.jobs)

    def idle_seconds(self):
        """idle seconds before next job should run"""
        next_job = self.get_next_job()
        return (next_job.next_run - self.env.now).total_seconds()

    async def schedule(self):
        """TODO: implement this."""
        pass


class Job(object):
    """
    A periodic job as used by :class:`JobMananger`.

    :param step: A quantity of a certain time unit
    :param job_manager: The :class:`JobMananger <JobMananger>` instance that
                      this job will register itself with once it has
                      been fully configured in :meth:`Job.do()`.
    :param unit: perioid unit, specified below.
    :param next_run: the `datetime <datetime.datetime>` that
                     the job will run, valid for `once` unit.
    :param job_id: the ID of the job object, can be None, system will generate one for you.

    Every job runs at a given fixed time interval that is defined by:

    * a :meth:`time unit second <Job.seconds>` or :meth:`time unit minite <Job.minutes>` etc.
    * a quantity of `time units` defined by `step`

    A job is usually created and returned by :meth:`JobMananger.run_every` method,
    which also defines its `interval` step, or by :meth:`JobMananger.run_once` method,
    which specified its run time.

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
    id_gen = get_id_gen(prefix='Job')
    unit_types = ['once', 'seconds', 'minutes', 'hours', 'days', 'weeks', 'months', 'years']

    def __init__(self, step, job_manager, unit=None, next_run=None, job_id=None):
        self.job_id = job_id
        self.unit = unit
        self.next_run = next_run
        self.job_manager = job_manager
        self.env = job_manager.env
        self.min_step = self.max_step = step

        self.last_run = None
        self.job_func = None
        self.event_kwargs = None
        self.tags = set()

        self.offset_dt = parse_dt('1970-01-01 00:00:00')

        if not self.job_id:
            self.job_id = next(Job.id_gen)

        self.event_name = 'TimerSource.%s' % (self.job_id)
        self.event_kwargs = {}

    def to(self, step):
        """
        Schedule the job to run at an irregular (randomized) step.

        The job's interval will randomly vary from the value given
        to  `run_every <JobMananger.run_every>` to `step`.
        The range defined is inclusive on both ends.
        For example, `every(A).to(B).seconds` executes
        the job function every N seconds such that A <= N <= B.

        :param step: Maximum interval between randomized job runs
        :return: The invoked job instance
        """
        self.max_step = int(step)
        assert self.max_step >= self.min_step
        return self

    def seconds(self):
        """run in second steps

        :return: The job instance
        """
        self.unit = 'seconds'
        return self

    def minutes(self):
        """run in minute steps

        :return: The job instance
        """
        self.unit = 'minutes'
        return self

    def hours(self):
        """run in hour steps

        :return: The job instance
        """
        self.unit = 'hours'
        return self

    def days(self):
        """run in day steps

        :return: The job instance
        """
        self.unit = 'days'
        return self

    def weeks(self):
        """run in week steps

        :return: The job instance
        """
        self.unit = 'weeks'
        return self

    def months(self):
        """run in month steps

        :return: The job instance
        """
        self.unit = 'months'
        return self

    def years(self):
        """run in year steps

        :return: The job instance
        """
        self.unit = 'years'
        return self

    def tag(self, *tags):
        """
        Tags the job with one or more unique indentifiers.

        Tags must be hashable. Duplicate tags are discarded.

        :param tags: A unique list of ``Hashable`` tags.
        :return: The invoked job instance
        """
        if not all(isinstance(tag, collections.Hashable) for tag in tags):
            raise TypeError('Tags must be hashable')
        self.tags.update(tags)
        return self

    def offset(self, offset_dt=None):
        """
        Schedule the job every step hours/days/weeks/months at a specific offset.

        :param offset_dt: a `datatime` str, like '1970-01-01 00:00:00', 'monday',
                          '09:32', '07-21', '21 14:12' and so on,
                          which must can be parsed by `dateutil.parser.parse`

        picks:

            * for hours: pick the offset_dt's minite and second field.
            * for days: pick the offset_dt's time field.
            * for weeks: pick the offset_dt's time field and weekday field.
            * for months: pick the offset_dt's time field and day field.

        :return: The invoked job instance
        """
        if self.unit == 'once':
            logger.warning('#Scheduler No offset should be set for timer runs only once.')
            return

        if not offset_dt:
            logger.warning('#Scheduler Call offset but no offset_dt specified.')
            return

        try:
            self.offset_dt = parse_dt(offset_dt)
        except (ValueError, TypeError):
            logger.warning('#Scheduler offset for time in invalid: %s, set to default: %s',
                           offset_dt,
                           self.offset_dt)

    def do(self, func, *args, **kwargs):
        """
        Specifies the func that should be called every time the job runs.

        Any additional arguments are passed on to func when the job runs.

        Actually, the the func is wrapped in an event callback function,
        when it's time to call the function, the `TimerSource` just generate the event,
        the function will be executed the the `Dispatcher.dispatch` dispatch the event.

        :param func: The function to be scheduled
        :return: The invoked job instance
        """
        assert self.unit in Job.unit_types
        self.event_kwargs.update({
            'func': func,
            'args': args,
            'kwargs': kwargs
            })

        self._schedule_first_run()
        logger.debug('#Scheduler Job do last_run: %s next_run: %s', self.last_run, self.next_run)
        self.job_manager.add_job(self)
        logger.info('#Scheduler New timer Job added: %s', self)
        self.job_manager.env.dispatcher.subscribe(self.event_name, event_callback)
        return self

    def gen_event(self):
        """Generate the event and schedule the next time of the timer event occurs."""
        event = Event(self.env, self.event_name, dt=self.next_run, **self.event_kwargs)
        if self.unit == 'once':
            self.job_manager.cancel(self)
        else:
            self.last_run = self.next_run
            self._schedule_next_run()

        logger.debug('#Scheduler generate new timer event %s, job last run: %s next run: %s',
                     event,
                     self.last_run,
                     self.next_run)

        return event

    def __lt__(self, other):
        """
        PeriodicJobs are sortable based on the scheduled time they
        run next.
        """
        return self.next_run < other.next_run

    def _schedule_first_run(self):
        """Compute the instant when this job should run the first time."""
        if self.max_step is not None:
            step = random.randint(self.min_step, self.max_step)
        else:
            step = self.min_step

        replay_dict = {}
        offset_dict = {}
        env = self.job_manager.env
        if self.offset_dt.year < env.now.year:
            replay_dict['year'] = env.now.year

        if self.unit == 'once':
            return
        if self.unit == 'weeks':
            offset_dict['days'] = step * 7
        else:
            offset_dict[self.unit] = step

        if self.unit == 'minutes':
            replay_dict['second'] = self.offset_dt.second
        if self.unit == 'hours':
            replay_dict['minute'] = self.offset_dt.minute
            replay_dict['second'] = self.offset_dt.second
        if self.unit == 'days':
            replay_dict['hour'] = self.offset_dt.hour
            replay_dict['minute'] = self.offset_dt.minute
            replay_dict['second'] = self.offset_dt.second
        if self.unit == 'months':
            replay_dict['day'] = self.offset_dt.day
            replay_dict['hour'] = self.offset_dt.hour
            replay_dict['minute'] = self.offset_dt.minute
            replay_dict['second'] = self.offset_dt.second
        if self.unit == 'years':
            replay_dict['month'] = self.offset_dt.month
            replay_dict['day'] = self.offset_dt.day
            replay_dict['hour'] = self.offset_dt.hour
            replay_dict['minute'] = self.offset_dt.minute
            replay_dict['second'] = self.offset_dt.second

        bench_dt = env.now.replace(**replay_dict)
        self.next_run = bench_dt + relativedelta(**offset_dict)
        while self.next_run < env.now:
            self.last_run = self.next_run
            self._schedule_next_run()

    def _schedule_next_run(self):
        """Compute the instant when this job should run next."""
        if self.unit == 'once':
            return True

        if self.max_step is not None:
            step = random.randint(self.min_step, self.max_step)
        else:
            step = self.min_step
        self.next_run = self.last_run + timedelta(**{self.unit: step})


class LiveTimerSource(AbsEventSource):
    """Live TimerEventSource, used for ``live`` mode"""
    _name = "LiveTimerEventSource"

    def __init__(self, env, *args, **kwargs):
        """init the event source"""
        self.env = env
        super().__init__(*args, **kwargs)
        self.job_manager = JobMananger(env)

    @property
    def name(self):
        """Name of the event_source"""
        return self._name

    async def gen_events(self, event_queue, limit_dt=None):
        """Generate new events for `Dispatcher`

        put all the generated/received or newly received events to
        event queue by call `Dispatcher.eq_put` , should not be blocked.
        only call by `Dispatcher` in **inner** mode, in **multithread** mode,
        the event source should run in parallel mode, and put the event to event queue.

        event_queue: put all the generated event to the event_queue
        limit_dt: for backtest, gen events before the limit_dt
        """
        while True:
            next_job = self.job_manager.get_next_job()
            if next_job and next_job.next_run <= self.env.now:
                event_queue.put(next_job.gen_event())
                if next_job.unit == 'once':
                    self.job_manager.cancel(next_job)
            else:
                # logger.debug('#Scheduler no job yet, sleep 1s.')
                await asyncio.sleep(1)

    def start(self):
        """initialize the event_source, start generate/receive events

        event_q: the event queue to put events to.
        """
        pass

    def stop(self):
        """stop the event_source, stop generate/receive events"""
        logger.info('#Scheduler timer source stopping, will clear all jobs.')
        self.job_manager.cancel_all_jobs()
        logger.debug('#Scheduler timer source stoped.')


class BackTimerSource(AbsEventSource):
    """Backtrack TimerEventSource, used for ``backtrack`` mode"""
    _name = "BackTrackTimerEventSource"

    def __init__(self, env, *args, **kwargs):
        """init the event source"""
        self.env = env
        self.job_manager = JobMananger(env)

    @property
    def name(self):
        """Name of the event_source"""
        return self._name

    async def gen_events(self, event_queue, limit_dt=None):
        """Generate new events for `Dispatcher`

        put all the generated/received or newly received events to
        event queue by call `Dispatcher.eq_put` , should not be blocked.
        only call by `Dispatcher` in **inner** mode, in **multithread** mode,
        the event source should run in parallel mode, and put the event to event queue.

        event_queue: put all the generated event to the event_queue
        limit_dt: for backtest, gen events befor the limit_dt
        """
        while True:
            next_job = self.job_manager.get_next_job()
            if next_job and next_job.next_run > limit_dt:
                break
            event_queue.put(next_job.gen_event())
            if next_job.unit == 'once':
                self.job_manager.cancel(next_job)

    def start(self):
        """initialize the event_source, start generate/receive events

        event_q: the event queue to put events to.
        """
        pass

    def stop(self):
        """stop the event_source, stop generate/receive events"""
        pass


def load_finchan_ext(env, *args, **kwargs):
    if env.run_mode == 'backtrack':
        timer_source = BackTimerSource(env)
    else:
        timer_source = LiveTimerSource(env)
    env.set_ext_obj(ext_name, timer_source.job_manager)
    env.dispatcher.register_event_source(timer_source)


def unload_finchan_ext(env):
    timer = env.timer
    env.timer = None
    timer.cancel_all_jobs()
    env.dispatcher.deregister_event_source(timer)


if __name__ == '__main__':
    # tests
    pass
