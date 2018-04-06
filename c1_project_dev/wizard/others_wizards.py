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
import subprocess
import os
import pip
# import pysftp
import logging

_logger = logging.getLogger(__name__)

class RemoteModulesBrowserWizard(models.TransientModel):
    _name = 'c1_project_dev.remote_module_browser'

    module_id = fields.Many2one('c1_project_dev.userdb.info', string='Database')
    module_ids = fields.One2many('c1_project_dev.c1_project_dev.module.info', 'module_id')
    filter_technical_name = fields.Char('Technical name')

    @api.multi
    def button_filter(self):
        if self.module_id.installed_modules:
            if self.filter_technical_name:
                # to_keep = self.module_id.installed_modules.filtered(lambda rec: (rec.name.find(self.filter_technical_name) > -1)).mapped('id')
                to_keep = self.module_id.installed_modules.search([('name','ilike',self.filter_technical_name)]).mapped('id')
                # to_keep.unlink()
                self.module_ids
            # print ''
        else:
            self.module_id.get_db_info()