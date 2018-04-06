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


class DockerInstanceManager(models.TransientModel):
    _name = 'c1_project_dev.docker_manager.wizard'

    def _default_info_ids(self):

        DockerConatiner = self.env['c1_project_dev.docker.container']
        Users = self.env['res.users']

        client = docker.from_env()
        data = []
        for container in client.containers.list():
            # _logger.info(container.attrs)
            user = Users.search([('docker_instance_id.containerid','=',container.attrs['Id'][:12])], limit=1)
            row_data = {
                'name': container.attrs['Name'],
                'image_name': container.attrs['Config']['Image'],
                'container_id': container.attrs['Id'][:12],
                'running': container.attrs['State']['Status'] == 'running' and True or False,
                'owner': user and user.id or False
            }
            data.append((0, 0, row_data))
            # _logger.info(container.attrs['Config'])
        return data

    info_ids = fields.One2many('c1_project_dev.docker_manager.line', 'wizard_id', string='Containers',
                               default=lambda self: self._default_info_ids())


class DockerInstanceManagerLine(models.TransientModel):
    _name = 'c1_project_dev.docker_manager.line'

    @api.multi
    def _compute_owner(self):
        # DockerContainer = self.env['c1_project_dev.docker.container']
        Users = self.env['res.users']
        for rec in self:
            user = Users.sudo().search([('docker_instance_id.containerid','=',rec.container_id)], limit=1)
            rec.owner = user and user.id

    wizard_id = fields.Many2one('c1_project_dev.docker_manager.wizard')
    name = fields.Char(string='Container name', required=True)
    container_id = fields.Char(string='Container ID', required=True)
    image_name = fields.Char(string='Image')
    running = fields.Boolean(string='Running')
    to_create = fields.Boolean(string='Create')
    # exists = fields.Boolean(string='Recorded in the System', compute,translate=True)
    owner = fields.Many2one('res.users', string='Assigned to', compute='_compute_owner')

