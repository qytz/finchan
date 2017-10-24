#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_finchan
----------------------------------

Tests for `finchan` module.
"""


import sys
import unittest
from contextlib import contextmanager
from click.testing import CliRunner

import finchan
from finchan.__main__ import main



class TestFinchan(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_000_something(self):
        pass

    def test_command_line_interface(self):
        runner = CliRunner()
        result = runner.invoke(main)
        help_result = runner.invoke(main, ['--help'])
        assert help_result.exit_code == 0
        assert '--help             Show this message and exit.' in help_result.output
