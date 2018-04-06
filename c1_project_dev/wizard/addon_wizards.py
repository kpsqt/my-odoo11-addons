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
from .svn_wizards import _CHECKOUT_WIZARD_ACTION
import subprocess
import os
import pip
# import pysftp
import logging

_logger = logging.getLogger(__name__)


class UserAddonsPathExplorer(models.TransientModel):
    _name = 'c1_project_dev.user_addons_path.wizard'

    # @api.onchange('filter_technical_name')
    # def _onchange_filter_technical_name(self):
    #     if self.filter_technical_name:
    #         return {
    #             'domain':{
    #                 'module_info_ids':[('name', 'like', self.filter_technical_name)]
    #             }
    #         }
    #     else:
    #         return {
    #             'domain': {
    #                 'module_info_ids': False
    #             }
    #         }

    @api.multi
    def button_filter(self):
        if self.filter_technical_name:
            to_rm = self.module_info_ids.filtered(lambda rec: not (rec.name.find(self.filter_technical_name) > -1))
            to_rm.unlink()
        else:
            self.module_info_ids.unlink()
            self.module_info_ids = self._default_module_info_ids()
        return True

    def _default_module_info_ids(self):
        addons_path = self.env.user.sudo().personal_addons_path
        addons = [f for f in os.listdir(addons_path) if os.path.isdir(os.path.join(addons_path, f))]
        data = []
        svn_account = self.env.user.sudo().svn_account
        svn_password = self.env.user.sudo().svn_password
        for addon in addons:
            row = {'name': addon, 'server_rev':-1, 'current_rev':-1}
            try:
                # destination_path = '%s/%s' % (self.env.user.personal_addons_path, self.name)
                destination_path = os.path.join(self.env.user.personal_addons_path, addon)
                local_svn = svn.local.LocalClient(destination_path)
                local_info = local_svn.info()
                row['is_svn'] = True
                row['current_rev'] = local_info['commit_revision']
                row['rev_author'] = local_info['commit_author']
                row['last_checkout_time'] = time.ctime(max(os.path.getmtime(root) for root,_,_ in os.walk(
                    os.path.join(addons_path, addon)
                )))

                repository_root = local_info['repository_root']
                repository_root = repository_root[:repository_root.rfind('/')]

                repo_id = self.env['c1_project_dev.repository'].search([('url', '=', repository_root)], limit=1)
                if repo_id:
                    _logger.warning(repository_root)
                    if repo_id.repository_type == 'svn':
                        try:
                            destination_path2 = os.path.join(repo_id.system_path or '', addon)
                            local_svn2 = svn.local.LocalClient(destination_path2)
                            local_info2 = local_svn2.info()
                            row['server_rev'] = local_info2['commit_revision']
                            module = self.env['c1_project_dev.module'].sudo().search([('technical_name', '=', addon)], limit=1)
                            if module:
                                # module.onserver_revision = remote_info['commit_revision']
                                module.sudo().write({
                                    'onserver_revision': local_info2['commit_revision'],
                                    'current_rev': local_info['commit_revision'],
                                })
                        except Exception as e:
                            _logger.exception(e)

                            # try:
                            #     # svn_repository_url = '%s/%s/trunk/%s' % (self.env.ref('c1_project_dev.qiyun').url, addon, addon)
                            #     repository_root = local_info['repository_root']
                            #     repository_root = repository_root[:repository_root.rfind('/')]
                            #
                            #     repo_id = self.env['c1_project_dev.repository'].search([('url','=',repository_root)], limit=1)
                            #
                            #     svn_repository_url = '%s/%s/trunk/%s' % (repository_root, addon, addon)
                            #     remote_svn = svn.remote.RemoteClient(svn_repository_url, username=repo_id and repo_id.username or '',
                            #                                          password=repo_id and repo_id.passwd or '')
                            #
                            #     remote_info = remote_svn.info()
                            #     row['server_rev'] = remote_info['commit_revision']
                            #     module = self.env['c1_project_dev.module'].sudo().search([('technical_name','=', addon)], limit=1)
                            #     if module:
                            #         # module.onserver_revision = remote_info['commit_revision']
                            #         module.sudo().write({
                            #             # 'onserver_revision': remote_info['commit_revision'],
                            #             'current_rev': local_info['commit_revision'],
                            #         })
                            # except SvnException as ex:
                            #     _logger.exception(ex)

            except (SvnException, EnvironmentError) as e:
                if type(e) is SvnException:
                    _logger.exception(e)
                    print(e)
                    # message = e.message
                    if 'E155007' in repr(e):
                        '''The directory exists but is not a working directory'''
                        # print '===The directory exists but is not a working directory==='
                        # row['is_svn'] = False
            except Exception as e2:
                _logger.exception(e2)
                _logger.warning('%s ignored in the %s addons path', (addon, self.env.user.sudo().name))
                continue
            data.append((0, 0, row))
        return data

    @api.multi
    def button_checkout(self):
        action = dict(_CHECKOUT_WIZARD_ACTION)
        menu = self.env.ref('c1_project_dev.menu_action_user_addons_path')
        action['name'] = 'Module checkout'
        action['res_model'] = 'c1_project_dev.module.copy.wizard'
        action['context'] = {
            'default_destination': self.env.user.sudo().personal_addons_path,
            # 'default_svn_repository_id': self.env.ref('c1_project_dev.qiyun').url,
            'default_svn_account': self.env.user.sudo().svn_account,
            'default_svn_password': self.env.user.sudo().svn_password,
            'hide_destination': True,
            'refresh_ui': True,
            'refresh_menu_id': menu.id,
        }
        return action


    @api.multi
    def button_svn_checkout(self):
        action = dict(_CHECKOUT_WIZARD_ACTION)
        menu = self.env.ref('c1_project_dev.menu_action_user_addons_path')
        action['name'] = 'SVN checkout'
        # action['res_model'] = 'c1_project_dev.module.copy.wizard'
        action['context'] = {
            'default_destination': self.env.user.sudo().personal_addons_path,
            # 'default_svn_repository_id': self.env.ref('c1_project_dev.qiyun').url,
            'default_svn_account': self.env.user.sudo().svn_account,
            'default_svn_password': self.env.user.sudo().svn_password,
            'hide_destination': True,
            'refresh_ui': True,
            'refresh_menu_id': menu.id,
        }
        return action

    user_id = fields.Many2one('res.users', string='User', default=lambda self:self.env.uid)
    module_info_ids = fields.One2many('c1_project_dev.user_addon.info', 'wizard_id',
        string='User', default=lambda self:self._default_module_info_ids())
    filter_technical_name = fields.Char('Technical name')


class UserAddonsInfo(models.TransientModel):
    _name = 'c1_project_dev.user_addon.info'

    # @api.multi
    # def _compute_to_upgrade(self):
    #     for rec in self:
    #         rec.to_upgrade = rec.current_rev

    wizard_id = fields.Many2one('c1_project_dev.user_addons_path.wizard')
    name = fields.Char(string='name')
    is_svn = fields.Boolean(string='Is SVN')
    current_rev = fields.Integer(string='Actual rev.', default=-1)
    server_rev = fields.Integer(string='Server current rev.', default=-1)
    rev_author = fields.Char(string='Rev. author')
    last_checkout_time = fields.Char(string='Last checkout')
    # to_upgrade = fields.Boolean(compute='_compute_to_upgrade')



    @api.multi
    def button_delete(self):
        path = os.path.join(self.env.user.sudo().personal_addons_path, self.name)
        shutil.rmtree(path)
        # action = dict(_CHECKOUT_WIZARD_ACTION)
        # action['target'] = 'inline'
        # action['res_model'] = 'c1_project_dev.user_addons_path.wizard'
        # action['name'] = 'Personal addons path manager'

        menu = self.env.ref('c1_project_dev.menu_action_user_addons_path')
        # return action
        return {
            'type':'ir.actions.client',
            'tag':'reload',
            'params': {
                'wait': True,
                'menu_id': menu.id,
            },
        }



    @api.multi
    def button_refresh(self):
        # self.env[''].create({
        #     'name': self.name,
        #     'destination': self.env.user.sudo().personal_addons_path,
        #     'svn_repository': self.env.ref('c1_project_dev.qiyun').url,
        #     'svn_account': self.env.user.sudo().svn_account,
        #     'svn_password': self.env.user.sudo().svn_password,
        # })
        Modules = self.env['c1_project_dev.module']
        module = Modules.search([('technical_name','=', self.name)], limit=1)
        menu = self.env.ref('c1_project_dev.menu_action_user_addons_path')
        action = dict(_CHECKOUT_WIZARD_ACTION)
        action['name'] = 'Module download'
        action['res_model'] = 'c1_project_dev.module.copy.wizard'
        action['context'] = {
            # 'default_name': self.name,
            'default_module_id': module.id,
            'default_destination': self.env.user.sudo().personal_addons_path,
            'default_svn_repository_id': module.repository_id.id,
            'default_svn_account': self.env.user.sudo().svn_account,
            'default_svn_password': self.env.user.sudo().svn_password,
            'hide_destination':True,
            'refresh_ui':True,
            'refresh_menu_id': menu.id,
        }
        # if self.is_svn:
        #     try:
        #         destination_path = os.path.join(self.env.user.personal_addons_path, self.name)
        #         local_svn = svn.local.LocalClient(destination_path)
        #         local_info = local_svn.info()
        #         repository_root = local_info['repository_root']
        #         repository_root = repository_root[:repository_root.rfind('/')]
        #         _logger.info(repository_root)
        #         repository_id = self.env['c1_project_dev.repository'].search([('url','=',repository_root)], limit=1)
        #         _logger.info(repository_id)
        #         action['context'].update({
        #             'default_svn_repository': repository_id and repository_id.id or False
        #         })
        #     except Exception as e:
        #         _logger.exception(e)

        return action


