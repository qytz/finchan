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
"""time event source"""
import time
import logging

from finchan.event import SysEvents

# name of the extension
ext_name = 'finchan.exts.timer_callback'
# required extension
required_exts = ['finchan.exts.timer_source']

logger = logging.getLogger(__name__)

logger = logging.getLogger()


def timer_call(env):
    logger.info(f'timer callback @ {env.now}')


def add_timer(event):
    scheduler = event.env.get_ext_obj('finchan.exts.timer_source')
    if event.env.run_mode == 'live_track':
        scheduler.run_every(3).to(5).seconds().do(timer_call)
    else:
        scheduler.run_every(3).to(15).minutes().do(timer_call)
    logger.info('#TimerCall timer job added')


def load_finchan_ext(env, process_time=3, *args, **kwargs):
    env.dispatcher.subscribe(SysEvents.SYSTEM_STARTED, add_timer)

def unload_finchan_ext(env):
    scheduler = env.get_ext_obj('finchan.exts.timer_source')
    scheduler.cancel()


if __name__ == '__main__':
    # tests
    pass
