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

from ..utils import file_utils

_logger = logging.getLogger(__name__)


class LogViewerWizard(models.TransientModel):
    _name = 'c1_project_dev.log_viewer.wizard'
    _description = 'Log Viewer'

    # def _default_log(self):
    #     logpath = self.env.user.sudo().personal_log_path
    #     with open(logpath, 'r') as logfile:
    #         # print ''.join(logfile.readlines()[10:])
    #         lines = logfile.readlines()
    #         if 2000 > len(lines) or self.line_number < 0:
    #             n = len(lines)
    #         else:
    #             n = self.line_number
    #         return ''.join( lines[-n:] )

    def _default_log(self):
        logpath = self.env.user.sudo().personal_log_path
        logfile = file_utils.BackwardsReader(logpath)
        lines = []
        line = logfile.readline()
        while line and len(lines)<2000:
            lines.append(line)
            line = logfile.readline()
        lines.reverse()
        return ''.join(lines)

    @api.multi
    def button_refresh_log(self):
        logpath = self.env.user.sudo().personal_log_path
        logfile = file_utils.BackwardsReader(logpath)
        lines = []
        line = logfile.readline()
        while line and len(lines) < self.line_number:
            lines.append(line)
            line = logfile.readline()
        lines.reverse()
        self.log = ''.join(lines)
        return True

    @api.onchange('line_number')
    def _onchange_line_number(self):
        logpath = self.env.user.sudo().personal_log_path
        for rec in self:
            logfile = file_utils.BackwardsReader(logpath)
            lines = []
            line = logfile.readline()
            while line and len(lines) < rec.line_number:
                lines.append(line)
                line = logfile.readline()
            lines.reverse()
            rec.log = ''.join(lines)

    # name = fields.Char()
    log = fields.Text(string="Log", default=lambda self: self._default_log(),
                      required=False)
    line_number = fields.Integer(string='Line number', default=2000)
    user_id = fields.Many2one(comodel_name="res.users", string="User",
                              required=False, default=lambda self:self.env.user,
                              readonly=True)





class OdooConfigFileViewerWizard(models.TransientModel):
    _name = 'c1_project_dev.config_file_log_viewer.wizard'

    def _default_config_line_ids(self):
        data = []
        filepath = self.env.context.get('default_name')
        if filepath:
            with open(filepath, 'r') as file:
                lines = file.readlines()
                lines = [ line for line in lines if not line.startswith(';') ]
                for line in lines:
                    entry = line.split('=')
                    if(len(entry) == 2):
                        data.append( (0, 0, {'name': entry[0], 'value': entry[1]}) )
        return data

    @api.multi
    def button_refresh(self):
        self.config_line_ids.unlink()
        if self.name:
            with open(self.name, 'r') as file:
                lines = file.readlines()
                # lines = [line for line in lines if (not line.startswith(';') and not line.startswith('['))]
                lines = [ line for line in lines if not line.startswith(';') ]
                data = []
                for line in lines:
                    entry = line.split('=')
                    if(len(entry) == 2):
                        data.append( (0, 0, {'name': entry[0], 'value': entry[1]}) )
                self.config_line_ids = data


    name = fields.Char(string='Config file path')
    config_line_ids = fields.One2many('c1_project_dev.config_file_line',
                                      'wizard_id', default=lambda self:self._default_config_line_ids(),
                                      string='Lines')


class OdooConfigFileLine(models.TransientModel):
    _name = 'c1_project_dev.config_file_line'

    wizard_id = fields.Many2one(comodel_name="c1_project_dev.config_file_log_viewer.wizard")
    name = fields.Char(string='Param')
    value = fields.Char(string='Value')




