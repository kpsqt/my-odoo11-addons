# -*- coding: utf-8 -*-
import base64
import datetime
import xmlrpc.client
from lxml import etree

import shutil
import docker

import importlib
import sys
import string
from traceback import print_exc, format_exception
import ast
import functools
import imp
import inspect
import itertools
import logging
import os
import pkg_resources
import re
import time
import types
import unittest
import threading
from operator import itemgetter
from os.path import join as opj

import odoo
import svn
from svn.exception import SvnException
import svn.common
import svn.remote
import svn.local
from odoo import api, fields, models, tools, SUPERUSER_ID, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import safe_eval
from odoo import modules
import subprocess
import os
import pip
# import pysftp
import logging
import threading

_logger = logging.getLogger(__name__)

class TestWizard(models.TransientModel):
    _name = 'c1_project_dev.test_wizard'

    _test_modules = {}
    def _get_unit_tests_selection(self):
        test_modules = odoo.modules.module.get_test_modules('c1_project_dev')
        # _logger.info(test_modules)
        self._test_modules = {test.__name__ : test for test in test_modules}
        # for test in self.test_modules:
        #     _logger.info(test.__name__)
        return [(test.__name__, test.__name__) for test in test_modules]

    @api.multi
    def button_execute_test(self):
        mod = self._test_modules.get(self.test_unit)
        global current_test

        threading.currentThread().testing = True

        tests = odoo.modules.module.unwrap_suite(unittest.TestLoader().loadTestsFromModule(mod))
        suite = unittest.TestSuite(t for t in tests if odoo.modules.module.runs_post_install(t))
        if suite.countTestCases():
            t0 = time.time()
            t0_sql = odoo.sql_db.sql_counter
            _logger.info('%s running tests.', mod.__name__)
            result = unittest.TextTestRunner(verbosity=2, stream=modules.module.TestStream(mod.__name__)).run(suite)
            if time.time() - t0 > 5:
                _logger.log(25, "%s tested in %.2fs, %s queries", mod.__name__, time.time() - t0, odoo.sql_db.sql_counter - t0_sql)
            if not result.wasSuccessful():
                # r = False
                _logger.error("Module %s: %d failures, %d errors", 'c1_project_dev', len(result.failures),len(result.errors))
        current_test = None
        threading.currentThread().testing = False
        return

    test_unit = fields.Selection(selection=_get_unit_tests_selection, string='Test cases')
