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


class SVNWizard(models.TransientModel):
    _name = 'c1_project_dev.svn_wizard'


    def _get_default(self, property):
        return self.env['ir.values'].sudo().get_default('ct_project.config.settings',
                                                                       property)

    @api.multi
    def execute(self):
        #         print '==========SENDING==============='
        #         print 'SVN SCRIPT PATH: ', self.env['ir.values'].sudo().get_default('ct_project.config.settings', 'ct_project_svn_script_path')
        #         print 'SVN ADDONS DIRECTORY: ', self.env['ir.values'].sudo().get_default('ct_project.config.settings', 'ct_project_addons_directory')
        #         print 'SVN LOG DIRECTORY: ', self.env['ir.values'].sudo().get_default('ct_project.config.settings', 'ct_project_logs_directory')
        #         print 'SVN PATH: ', self.svn_repository
        #         print 'SVN ACCOUNT: ', self.sender_svn_account
        #         print 'SVN PASSWORD: ', self.sender_svn_password
        #         print 'MODULE NAME: ', self.name
        #         print 'MODULE VERSION: ', self.version
        # print sys.version

        '''update the task stage'''
        if self.task_id:
            self.task_id.with_context(from_ui=False).write({'stage_id': self._get_default('ct_project_upload_stage')})

        '''running the script'''
        cmd_script = False
        proc = None
        if not self.version:
            cmd_script = '%s %s %s %s %s %s %s' % (
                self._get_default('ct_project_svn_script_path'),
                self.svn_repository,
                self.sender_svn_account,
                self.sender_svn_password,
                self._get_default('ct_project_addons_directory'),
                self._get_default('ct_project_logs_directory'),
                self.name)
        #             proc = subprocess.Popen([
        #                 self.env['ir.values'].sudo().get_default('ct_project.config.settings', 'ct_project_svn_script_path'),
        #                 self.svn_repository,
        #                 self.sender_svn_account,
        #                 self.sender_svn_password,
        #                 self.env['ir.values'].sudo().get_default('ct_project.config.settings', 'ct_project_addons_directory'),
        #                 self.env['ir.values'].sudo().get_default('ct_project.config.settings', 'ct_project_logs_directory'),
        #                 self.name
        #             ], stdout=subprocess.PIPE)
        else:
            cmd_script = '%s %s %s %s %s %s -r %s %s' % (
                self._get_default('ct_project_svn_script_path'),
                self.svn_repository,
                self.sender_svn_account,
                self.sender_svn_password,
                self._get_default('ct_project_addons_directory'),
                self._get_default('ct_project_logs_directory'),
                self.version,
                self.name)
        #             proc = subprocess.Popen([
        #                 self.env['ir.values'].sudo().get_default('ct_project.config.settings', 'ct_project_svn_script_path'),
        #                  self.svn_repository,
        #                  self.sender_svn_account,
        #                  self.sender_svn_password,
        #                  self.env['ir.values'].sudo().get_default('ct_project.config.settings', 'ct_project_addons_directory'),
        #                  self.env['ir.values'].sudo().get_default('ct_project.config.settings', 'ct_project_logs_directory'),
        #                  self.version,
        #                  self.name
        #             ], stdout=subprocess.PIPE)
        # svn_cmd = 'svn log svn://repo.qitong.work/odoo/ct_project_uf --username jgq@cotong.com --password c34b865d24d9be7cb8145b2c2f120664'
        #
        # print cmd_script
        stream = os.popen(cmd_script).read()
        # print stream

        #         '''Update modules list'''
        #         self.env['base.module.update'].sudo().create({
        #             'state':'init',
        #         }).update_module()
        #
        #         '''Installing the module'''
        #         if self.auto_install:
        #             module = self.env['ir.module.module'].sudo().search([('name','=',self.name)], limit=1)
        #             if not module:
        #                 raise UserError(_("Could'nt find the transfered the module. Some error happened."))
        #
        #             '''force server restart to reload python code before upgrading or installing'''
        #             self._cr.commit()
        #             odoo.service.server.restart()
        #             odoo.modules.module.loaded.remove(module.name)
        #             odoo.service.server.load_server_wide_modules()
        #
        #             if module.state == 'installed':
        #                 module.button_immediate_upgrade()
        #             else:
        #                 module.button_immediate_install()
        #
        #         '''Reloading the user interface'''
        #         if self.reload:
        #             menu = self.env.ref('project.menu_main_pm')
        #             return{
        #                 'type':'ir.actions.client',
        #                 'tag':'reload',
        #                 'params': {'wait': True,'menu_id':menu and menu.id or False},
        #             }
        return {'type': 'ir.actions.act_window_close'}

    @api.multi
    def execute_py_svn(self):
        svn_repository_url = '%s/%s/trunk/%s' % (self.svn_repository, self.name, self.name)
        try:
            remote_svn = svn.remote.RemoteClient(svn_repository_url, username=self.sender_svn_account,
                                                 password=self.sender_svn_password)
            # remote_info = remote_svn.info()
            destination_path = '%s/%s' % (self.env.user.sudo().personal_addons_path, self.name)
            # destination_path = '%s/%s' % (self._get_default('ct_project_addons_directory'), self.name)

            local_svn = svn.local.LocalClient(destination_path, username=self.sender_svn_account,
                                              password=self.sender_svn_password)
            local_info = local_svn.info()
            # print 'local current revision %s' % local_info['commit_revision']

            args = [destination_path]
            if self.version:
                args.append('-r %s' % self.version)
                args.append('--force')

            local_svn.run_command(subcommand='update', return_binary=True, args=args)
            local_info = local_svn.info()

            # print 'updated! current revision %s' % local_info['commit_revision']

            self._update_task_stage(local_svn, local_info=local_info)

        except (SvnException, EnvironmentError) as e:
            if type(e) is SvnException:
                _logger.exception(e)
                message = e.message

                if 'E155007' in message:
                    '''The directory exists but is not a working directory'''
                    # print '===The directory exists but is not a working directory==='
                    self._checkout(remote_svn, destination_path, force=True)

                elif 'E170001' in message:
                    raise UserError(_("Authentification error: check your svn credentials (user/password)."))

                elif 'E170013' in message:
                    raise UserError(_("Unable to connect to a repository at URL '%s'. Make sure the provided url is valid and your credentials as well.") % svn_repository_url)

                else:
                    raise UserError(_("An error happened during the process: \n%s.") % message)

            elif type(e) is EnvironmentError:
                '''The directory doesnt exists'''
                # print '==The directory doesnt exists=='
                self._checkout(remote_svn, destination_path)


        # '''Update modules list'''
        # self.env['base.module.update'].sudo().create({
        #     'state':'init',
        # }).update_module()
        #
        # module = self.env['ir.module.module'].sudo().search([('name', '=', self.name)], limit=1)
        # if not module:
        #     raise UserError(_("Could'nt find the transferred the module. Some error happened."))

        # '''Installing the module'''
        # if self.auto_install:
        #     module = self.env['ir.module.module'].sudo().search([('name','=',self.name)], limit=1)
        #     if not module:
        #         raise UserError(_("Could'nt find the transfered the module. Some error happened."))
        #
        #
        #     if module.sudo().state == 'installed':
        #         module.sudo().state = 'to upgrade'
        #     elif module.sudo().state == 'uninstalled':
        #         module.sudo().state = 'to install'
        #
        #     '''force server restart to reload python code before upgrading or installing'''
        #     self._cr.commit()
        #     odoo.service.server.restart()
        #     # odoo.modules.module.loaded.remove(module.name)
        #     # odoo.service.server.load_server_wide_modules()

        # if self.reload:
        #     #menu = self.env.ref('project.menu_main_pm')
        #     active_project = self.env.context.get('active_project')
        #     if active_project:
        #         action = self.env.ref('project.act_project_project_2_project_task_all').read()[0]
        #         #print action['context'].replace(" ","").replace("\n","")
        #         str = action['context'].replace(" ","").replace("\n","").replace("active_id","''")
        #         #print str
        #         ctx = ast.literal_eval(str)
        #         ctx.update({
        #             'active_id': active_project,
        #             'active_ids': [active_project],
        #             'search_default_project_id': active_project
        #         })
        #         #print action
        #         return {
        #             'type': action['type'],
        #             'view_type': action['view_type'],
        #             'view_mode': action['view_mode'],
        #             'context': ctx,
        #             'res_model': action['res_model'],
        #             'filter': action['filter'],
        #             'limit': action['limit'],
        #             'name': action['name'],
        #             'target':'main'
        #         }

        if self.restart_docker:
            if self.env.user.sudo().docker_instance_id:
                self.env.user.sudo().docker_instance_id.action_restart()

        return {'type': 'ir.actions.act_window_close'}

    @api.multi
    def execute_transfer_revert(self):
        return

    def _update_task_stage(self, local_client, local_info=None):
        '''update the task stage'''
        if self.task_id:
            data = {}
            # upload_stage_id = self._get_default('ct_project_upload_stage')
            # upload_stage = upload_stage_id and self.env['project.task.type'].browse([upload_stage_id])[0] or False

            # if self.update_stage:
            #     if self.state == 'transfer' and upload_stage:
            #         data['stage_id'] = upload_stage.id
            #     elif self.state == 'revert' and self.revert_stage:
            #         data['stage_id'] = self.revert_stage.id
            #     elif self.state == 'revert' and upload_stage:
            #         data['stage_id'] = upload_stage.parent_stage and upload_stage.parent_stage.id or upload_stage.id

            local_info = local_info and local_info or local_client.info()
            log_data = [(0, _,{'log_date': entry.date, 'message': entry.msg, 'revision': entry.revision,'author': entry.author, 'operation_type': self.state, 'tag':self.tag})
                        for entry in local_client.log_default(revision_from=local_info['commit_revision'], revision_to=local_info['commit_revision'])]

            if len(log_data):
                data.update({'transfer_ids': log_data})
            #print data
            self.task_id.with_context(from_ui=False).write(data)


    def _checkout(self, remote_client, destination_path, force=False):
        try:
            #remote_client.checkout(destination_path, force=force)
            if self.version:
                remote_client.checkout(destination_path, revision=bool(self.version) and self.version or False)
            else:
                remote_client.checkout(destination_path)

            local_svn = svn.local.LocalClient(destination_path, username=self.sender_svn_account,
                                              password=self.sender_svn_password)
            local_info = local_svn.info()
            # print 'revision %s checked out' % local_info['commit_revision']
            #
            self._update_task_stage(local_svn, local_info)

        except Exception as e:
            _logger.exception(e)
            raise UserError(_("An error happened during the process: \n%s.") % e.message)



    def _default_get_auto_install(self):
        return self._get_default('ct_project_auto_install')

    @api.onchange('name')
    def _onchange_name(self):
        # print '********On Change Name********'
        if self.version:
            return
        if self.state == 'transfer':
            try:
                svn_repository_url = '%s/%s/trunk/%s' % (self.svn_repository, self.name, self.name)
                remote_svn = svn.remote.RemoteClient(svn_repository_url, username=self.sender_svn_account,
                                                 password=self.sender_svn_password)
                info = remote_svn.info()
                last_commit = info['commit_version']
                self.version = last_commit
            except Exception as e:
                e.message

    @api.onchange('version')
    def _onchange_revision(self):
        # print '********On Revision********'
        if self.version:
            try:
                svn_repository_url = '%s/%s/trunk/%s' % (self.svn_repository, self.name, self.name)
                remote_svn = svn.remote.RemoteClient(svn_repository_url, username=self.sender_svn_account,
                                                 password=self.sender_svn_password)

                text = ''
                for log in remote_svn.log_default(revision_from=self.version, revision_to=self.version):
                    # print log
                    text = text + '%s : %s\n' % (log.date, log.msg)
                # print text
                self.revision_message = text
            except Exception as e:
                _logger.error(e.message)
                # print e.message
                # e.message

    # @api.onchange('revert_stage')
    # def _onchange_revert_stage(self):
    #     upload_stage = self.env['project.task.type'].search([('id', '=', self._get_default('ct_project_upload_stage'))],
    #                                                         limit=1)
    #     if self.revert_stage and self.revert_stage.sequence > upload_stage.sequence:
    #         return {'warning': {
    #             'title': _('Warning'),
    #             'message': _(
    #                 'The stage to revert the task to should be a previous stage to the stage "%s"' % upload_stage and upload_stage.name or False),
    #         }}

    @api.constrains('revert_stage')
    def _check_revert_stage(self):
        upload_stage = self.env['project.task.type'].search([('id', '=', self._get_default('ct_project_upload_stage'))],
                                                            limit=1)
        if self.revert_stage and self.revert_stage.sequence > upload_stage.sequence:
            raise ValidationError(_(
                'The stage to revert the task to should be a previous stage to the stage "%s"' % (upload_stage and upload_stage.name or False)))

        if (self.task_id and self.revert_stage) and (self.revert_stage not in self.task_id.project_id.type_ids):
            # self.revert_stage = False
            raise ValidationError(_('Incorrect stage'))

    def _get_revisions(self):
        revs = [(False,'HEAD')]
        module_name = self.env.context.get('default_name')
        svn_repository = self.env.context.get('default_svn_repository')
        sender_svn_account = self.env.context.get('default_sender_svn_account')
        sender_svn_password = self.env.context.get('default_sender_svn_password')
        try:
            svn_repository_url = '%s/%s' % (svn_repository, module_name)
            remote_svn = svn.remote.RemoteClient(svn_repository_url, username=sender_svn_account,
                                             password=sender_svn_password)
            info = remote_svn.info()
            last_commit_revison = info['commit_revision']
            #print last_commit_revison
            #revs.append((str(last_commit_revison), 'HEAD'))
            for i in range(1, last_commit_revison + 1):
                revs.append( (str(i),str(i)) )
        except Exception as e:
            # print e.message
            _logger.error(e.message)
        #print revs
        return revs

    @api.onchange('revert_stage')
    def onchange_revert_stage(self):
        if (self.task_id and self.revert_stage) and (self.revert_stage not in self.task_id.project_id.type_ids):
            self.revert_stage = False
            return {
                'warning': {
                    'title': _('Warning'),
                    'message': _('The stage to revert the task to should belong to the project "%s"' % self.task_id.project_id.name or ''),
                }
            }
        current_stage_id = self.env.context.get('current_stage')
        current_stage = self.env['project.task.type'].search([('id', '=', current_stage_id)], limit=1)
        if current_stage:
            return {
                'domain': {'revert_stage':[('sequence','<',current_stage.sequence)]}
            }

    # @api.onchange('task_id')
    # def onchange_task(self):
    #     current_stage_id = self.env.context.get('current_stage')
    #     current_stage = self.env['project.task.type'].search([('id', '=', current_stage_id)], limit=1)
    #     if current_stage:
    #         return {
    #             'domain': {'revert_stage':[('sequence','<',current_stage.sequence)]}
    #         }

    def _get_default_revert_stage(self):
        current_stage_id = self.env.context.get('current_stage')
        upload_stage_id = self._get_default('ct_project_upload_stage')
        if current_stage_id and current_stage_id == upload_stage_id:
            return self.env['project.task.type'].search([('id','=',upload_stage_id)], limit=1).parent_stage

    name = fields.Char(string='Module name', required=True)
    svn_repository = fields.Char(string='SVN base repository', required=True, tranlated=True)
    #version = fields.Integer(string='Revision')
    state = fields.Selection([('transfer','Transfer'),('revert','Revert')], default='transfer')
    version = fields.Selection(_get_revisions, string='Revision')
    sender_svn_account = fields.Char(string='Sender\'s SVN account', required=True)
    sender_svn_password = fields.Char(string='Sender\'s SVN password', required=True)
    restart_docker = fields.Boolean(string='Restart container', default=True)
    auto_install = fields.Boolean(string='Auto-install', help='Auto-install the module soon after transfer',
                                  tranlated=True, default=lambda self: self._default_get_auto_install())
    task_id = fields.Many2one('project.task', string='Task')
    revert_stage = fields.Many2one('project.task.type', string='Return to stage',
                                   default=lambda self: self._get_default_revert_stage())
    current_revision = fields.Integer(string='Current revision', related='task_id.current_transfer_revision')
    tag = fields.Selection([('good','Good'),('bad','Bad')], string='Tag')
    update_stage = fields.Boolean(string='Update stage', default=True)
    revision_message = fields.Text(string='Revision message')


    def install_module(self, module_name, reload):
        return


_CHECKOUT_WIZARD_ACTION = {
    'name': 'SVN Checkout',
    'type': 'ir.actions.act_window',
    'res_model': 'c1_project_dev.svn_checkout_wizard',
    'view_mode': 'form',
    'target': 'new'
}


class SvnCheckoutWizard(models.TransientModel):
    _name = 'c1_project_dev.svn_checkout_wizard'

    @api.multi
    def button_checkout(self):
        try:
            svn_repository_url = '%s/%s/trunk/%s' % (self.svn_repository_id and self.svn_repository_id.url or False, self.module_id.technical_name, self.module_id.technical_name)
            # destination_path = '%s/%s' % (self.destination, self.module_id.technical_name)
            destination_path = os.path.join(self.destination, self.module_id.technical_name)
            # _logger.info(svn_repository_url)
            remote_client = svn.remote.RemoteClient(svn_repository_url, username=self.svn_repository_id.username,
                                                 password=self.svn_repository_id.passwd)

            if bool(self.rev):
                remote_client.checkout(destination_path, revision=self.rev)
            else:
                remote_client.checkout(destination_path, revision=None)

            local_svn = svn.local.LocalClient(destination_path)
            local_info = local_svn.info()
            # print 'revision %s checked out' % local_info['commit_revision']
            # _logger.info('%s#%s checked out to %s', (svn_repository_url, self.rev, destination_path))
            if self.restart_container:
                if self.env.user.sudo().docker_instance_id:
                    self.env.user.sudo().docker_instance_id.action_restart()
        except Exception as e:
            _logger.exception(e)
            raise UserError(_("An error happened during the process: \n%s.") % e)

        if self.env.context.get('refresh_ui'):
            params = {'wait': True}
            if self.env.context.get('refresh_menu_id'):
                params['menu_id'] = self.env.context.get('refresh_menu_id')
            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
                'params':params
            }
        return True

    # @api.onchange('revision')
    # def _onchange_revision(self):
    #     for rec in self:
    #         rec.rev = self.revision

    # def _get_revisions(self, path=None, base_url=None, username=None, password=None):
    #     revs = [(False,'HEAD')]
    #     module_name = self.env.context.get('default_name')
    #     svn_repository = self.env.context.get('default_svn_repository')
    #     svn_account = self.env.context.get('default_svn_account')
    #     svn_password = self.env.context.get('default_svn_password')
    #     try:
    #         svn_repository_url = '%s/%s' % (svn_repository, module_name)
    #         remote_svn = svn.remote.RemoteClient(svn_repository_url, username=svn_account,
    #                                          password=svn_password)
    #         info = remote_svn.info()
    #         last_commit_revison = info['commit_revision']
    #         #print last_commit_revison
    #         #revs.append((str(last_commit_revison), 'HEAD'))
    #         for i in range(1, last_commit_revison + 1):
    #             revs.append( (str(i),str(i)) )
    #     except Exception as e:
    #         print e.message
    #     #print revs
    #     return revs

    @api.onchange('svn_repository_id')
    def _onchange_module_id(self):
        if self.svn_repository_id:
            return {
                'domain':{
                    'module_id':[('repository_id','=',self.svn_repository_id and self.svn_repository_id.id or False)]
                }
            }

    module_id = fields.Many2one('c1_project_dev.module', string='Module')
    # name = fields.Char(string='Module name', required=True)
    # svn_repository = fields.Char(string='SVN URL', required=True)
    svn_repository_id = fields.Many2one('c1_project_dev.repository', string='Svn repository')
    svn_account = fields.Char(string='SVN account')
    svn_password = fields.Char(string='SVN password')
    # revision = fields.Selection(_get_revisions, string='Revision')
    rev = fields.Integer(string='Revision')
    destination = fields.Char(string='Destination')
    restart_container = fields.Boolean(string='Restart container', default=True)
