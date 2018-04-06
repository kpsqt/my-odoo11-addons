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


class LinuxCmdWizardLine(models.TransientModel):
    _name = 'c1_project_dev.linux_cmd.line'

    wizard_id = fields.Many2one('c1_project_dev.linux_cmd.wizard')
    command_id = fields.Many2one('c1_project_dev.command', string='Command', ondelete='set null', required=True)
    cmd_type = fields.Selection(string='Command type', related='command_id.type', readonly=True)
    cmd_args_mandatory = fields.Boolean(related='command_id.params_mandatory', readonly=True)
    cmd_args = fields.Char(string='Command args')
    sequence = fields.Integer(string='')



class LinuxCmdWizard(models.TransientModel):
    _name = 'c1_project_dev.linux_cmd.wizard'


    # def _default_cmd_lines(self):
    #     Commands = self.env['c1_project_dev.command']
    #     res = [(0, 0, {
    #         'command_id': cmd.id,
    #         }) for cmd in Commands.search([('id','!=',False)])]
    #     return res

    # @api.onchange('state')
    # def onchange_state(self):
    #     print '===onchange_state==='
    #     if self.state == 'single':
    #         return {
    #             'attrs': {
    #                 'cmd_args': {'invisible':[('cmd_type','!=','with_parameter')],'required':[('cmd_args_mandatory','=',True)]},
    #             }
    #         }
    #     elif self.state == 'multiple':
    #         return {
    #             'attrs': {
    #                 'cmd_args': {},
    #             }
    #         }

    @api.constrains('cmd_args')
    def _check_cmd_args(self):
        for r in self:
            match = re.search(r'rm|\||&', r.cmd_args or '', re.M | re.I)
            if match:
                raise ValidationError(_('Input such as "rm", "|", "&" are forbidden'))

    state = fields.Selection([('single','Run single command'), ('multiple','Run multiple commands')], string='Type', default='single', translate=True)
    command_id = fields.Many2one('c1_project_dev.command', string='Command', ondelete='set null')
    cmd_type = fields.Selection(string='Command type', related='command_id.type', readonly=True)
    cmd_args = fields.Char(string='Command args')
    cmd_args_mandatory = fields.Boolean(related='command_id.params_mandatory', readonly=True)
    cmd_description = fields.Text(related='command_id.description', readonly=True)
    cmd_preview = fields.Char(string='Command preview')
    linux_username = fields.Char(string='Linux username')
    linux_password = fields.Char(string='Linux password')
    output = fields.Text(string='Command output', readonly=True)
    # cmd_line_ids = fields.One2many('c1_project_dev.linux_cmd.line', 'wizard_id', default=lambda self: self._default_cmd_lines())
    cmd_line_ids = fields.One2many('c1_project_dev.linux_cmd.line', 'wizard_id')

    @api.onchange('command_id','cmd_args')
    def onchange_command(self):
        for rec in self:
            if rec.command_id:
                if rec.command_id.type == 'with_parameter' and rec.cmd_args:
                    rec.cmd_preview = '%s %s' % (rec.command_id.command, rec.cmd_args)
                else:
                    rec.cmd_preview = rec.command_id.command
            else:
                rec.cmd_preview = ''

    @api.multi
    def execute(self):
        if self.command_id:
            try:
                output = self.command_id.run(self.cmd_args, no_exception=True)
                self.write({'output':output})
            except Exception as e:
                raise UserError(e.message)
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'form_type': 'form',
            'view_mode': 'form',
            'view_id': self.env.ref('c1_project_dev.cmd_wizard_form_view').id,
            'context': {'default_cmd_preview': self.cmd_preview},
            'res_id': self.id,
            'target': 'new',
        }

    @api.multi
    def execute_multiple(self):
        lines = self.cmd_line_ids.sorted(lambda r: r.sequence)
        for index in range(len(lines)):
            line = lines[index]
            try:
                output = line.command_id.run(line.cmd_args, no_exception= (line == lines[-1]))
                self.write({'output': '%s%s\n-----------------------------------\n' % ( self.output or '' , output) })
            except Exception as e:
                self.write({'output': '%s%s\n-----------------------------------\n' % ( self.output or '', e.message)})
                raise UserError(e.message)
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'form_type': 'form',
            'view_mode': 'form',
            'view_id': self.env.ref('c1_project_dev.cmd_wizard_form_view').id,
            # 'context': {'default_cmd_preview': self.cmd_preview},
            'res_id': self.id,
            'target': 'new',
        }

