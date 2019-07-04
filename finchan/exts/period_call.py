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
import logging

# name of the extension
ext_name = "finchan.exts.period_call"
# required extension
required_exts = ["finchan.exts.scheduler"]

logger = logging.getLogger(__name__)


async def run(env):
    async for dt in env.ext_ns.scheduler(env).every(3).to(8).seconds():
        logger.info("# period_call running periodly @%s", dt)

async def setup(env):
    env.dispatcher.schedule_task(run(env))


async def cleanup(env):
    pass

def load_finchan_ext(env):
    pass


if __name__ == "__main__":
    # tests
    pass
