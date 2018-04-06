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

import docker
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


class ModuleDependencyCheckWizard(models.TransientModel):
    _name = 'c1_project_dev.module_dependencies.wizard'

    # def __init__(self, pool, cr):

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        result = super(ModuleDependencyCheckWizard, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        # print(result)
        return result

    @api.multi
    def button_install_dependencies(self):
        # print '***Install Clicked***'
        # print len(self.dependencies)
        for dep in self.dependencies.sorted(key='sequence').filtered(lambda rec: not rec.installed):
            # print '***Install Clicked***'
            if dep.install_method is False:
                raise UserError(_('Please choose the installation method for \'%s\'.') % dep.name)
            # if dep.install_method == 'pip':
            #     try:
            #         out = pip.main(['install', dep.name])
            #         # print out
            #         # if out == 2:
            #         #     raise UserError(_('Pip failed installing \'%s\'. Exit status: %s.') % (dep.name, out))
            #     # except SystemExit as e:
            #     #     raise UserError(_('Installation Failded: %s') % e.message)
            #     except Exception as e:
            #         raise UserError(_('Pip failed installing \'%s\': %s.') % (dep.name, e))

            if dep.install_method == 'pip':
                output = self.env.ref('c1_project_dev.cmd_docker_pip_install').run(dep.name)
            elif dep.install_method == 'easy_install':
                output = self.env.ref('c1_project_dev.cmd_docker_easy_install').run(dep.name)

            _logger.info(output)

        self.dependencies.unlink()
        self.write({'dependencies': self._dependencies_line_helper(self.module_id)})

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode':'form',
            'view_type':'form',
            'res_id': self.id,
            'target':'new',
        }

    def _dependencies_line_helper(self, module):
        data = []
        if module.python_dependencies:
            dependencies = module.python_dependencies.strip().split(',')
            # installed_distributions = pip.get_installed_distributions()
            # installed_deps = [i.key for i in installed_distributions]
            output = self.env.ref('c1_project_dev.cmd_docker_exec').run('pip freeze')
            # _logger.info(output)

            installed_distributions = [dep for dep in output.split('\n') if
                                       not (dep.startswith('Warning:') or dep.startswith('##') or (dep == ''))]
            _logger.info(installed_distributions)
            installed_deps = [i.split('==')[0] for i in installed_distributions]
            installed_deps_versions = [i.split('==')[1] for i in installed_distributions]

            for dep in dependencies:
                installed = dep in installed_deps
                data.append((0, 0, {
                    'name': dep,
                    'installed': installed,
                    'installed_version': installed and installed_deps_versions[
                        installed_deps.index(dep)] or False,
                    'install_method': installed and False or 'pip',
                    'to_install': not installed
                }))
        # print data
        return data


    def _dependencies_default(self):
        # print '***DEFAULT***'
        module_id = self.env.context.get('default_module_id')
        # print module_id
        if not module_id:
            return

        module = self.env['c1_project_dev.module'].search([('id','=',module_id)])
        if not module:
            return
        return self._dependencies_line_helper(module)

    @api.onchange('module_id')
    def onchange_module(self):
        # print '===ONCHANGE===',self.module_id
        if self.module_id:
            data = []
            if self.module_id.python_dependencies:
                dependencies = self.module_id.python_dependencies.strip().split(',')
                # installed_distributions = pip.get_installed_distributions()
                # installed_deps = [i.key for i in installed_distributions]
                # installed_deps_versions = [i.version for i in installed_distributions]
                output = self.env.ref('c1_project_dev.cmd_docker_exec').run('pip freeze')
                installed_distributions = [dep for dep in output.split('\n') if
                                           not (dep.startswith('Warning:') or dep.startswith('##') or (dep == ''))]
                _logger.info(installed_distributions)
                installed_deps = [i.split('==')[0] for i in installed_distributions]
                installed_deps_versions = [i.split('==')[1] for i in installed_distributions]

                for dep in dependencies:
                    installed = dep in installed_deps
                    data.append((0, 0, {
                        'name': dep,
                        'installed': installed,
                        'installed_version': installed and installed_deps_versions[
                        installed_deps.index(dep)] or False,
                        'install_method': installed and False or 'pip',
                        'to_install': not installed
                    }))
                # print data
                self.dependencies = data
        # self.dependencies = []

    module_id = fields.Many2one('c1_project_dev.module', string='Module')
    satisfied = fields.Boolean(string='Dependencies satisfied', related='module_id.installable', readonly=True)
    dependencies = fields.One2many('c1_project_dev.module_dependencies.line', 'wizard_id',
     default=lambda self: self._dependencies_default(), string='Dependencies lines')


class ModuleDependencyCheckLine(models.TransientModel):
    _name = 'c1_project_dev.module_dependencies.line'

    INSTALL_METHODS = [('pip','Pip'), ('easy','Easy Install')]

    # @api.multi
    # def button_install(self):
    #     print '***Install Clicked***'
    #     if self.install_method is False:
    #         raise UserError(_('Please choose the installation method.'))
    #
    #     if self.install_method == 'pip':
    #         try:
    #             pip.main(['install', self.name])
    #         except SystemExit as e:
    #             raise UserError(_('Installation Failded: %s') % e.message)
    #
    #     return

    sequence = fields.Integer(string='Sequence')
    wizard_id = fields.Many2one('c1_project_dev.module_dependencies.wizard', ondelete='cascade', string='Module')
    name = fields.Char(string='Python module')
    installed_version = fields.Char(string='Version')
    installed = fields.Boolean(string='Installed')
    to_install = fields.Boolean(string='To install')
    install_method = fields.Selection(selection=INSTALL_METHODS, index=True, string='Installation method', default='pip')


class ModuleInstallerWizard(models.TransientModel):
    _name = 'c1_project_dev.module.wizard'

    @api.onchange('database_id')
    def _onchange_database_id(self):
        for record in self:
            record.login = record.database_id and record.database_id.login or ''
            record.passwd = record.database_id and record.database_id.passwd or ''

    # @api.depends('module_id')
    # def _compute_on_server_rev(self):
    #     for rec in self:
    #         if rec.repository_id:
    #             try:
    #                 svn_repository_url = '%s/%s/trunk/%s' % (rec.repository_id.url, rec.module_id.technical_name, rec.module_id.technical_name)
    #                 remote_svn = svn.remote.RemoteClient(svn_repository_url, username=self.env.user.sudo().svn_account,
    #                                                          password=self.env.user.sudo().svn_password)
    #                 remote_info = remote_svn.info()
    #                 _logger.info(remote_info)
    #                 rec.on_server_rev = remote_info['commit_revision']
    #             except Exception as e:
    #                 _logger.exception(e)

    @api.onchange('module_id')
    def _onchange_module(self):
        # print '*******ONCHANGE MODULE ID********'
        for rec in self:
            if rec.repository_id:
                try:
                    svn_repository_url = '%s/%s/trunk/%s' % (rec.repository_id.url, rec.module_id.technical_name, rec.module_id.technical_name)
                    remote_svn = svn.remote.RemoteClient(svn_repository_url, username=self.env.user.sudo().svn_account,
                                                             password=self.env.user.sudo().svn_password)
                    remote_info = remote_svn.info()
                    _logger.info(remote_info)
                    rec.on_server_rev = remote_info['commit_revision']
                except Exception as e:
                    _logger.exception(e)

    module_id = fields.Many2one('c1_project_dev.module', string='Module')
    current_downloaded_rev = fields.Integer(string='Downloaded revision', related='module_id.current_downloaded_rev')
    # on_server_rev = fields.Integer(string='Revision on server', compute='_compute_on_server_rev')
    on_server_rev = fields.Integer(string='Revision on server')
    installable = fields.Boolean(related='module_id.installable', string='Installable')
    database_id = fields.Many2one('c1_project_dev.userdb.info', string='Database')
    repository_id = fields.Many2one('c1_project_dev.repository', string='Repository')
    login = fields.Char(string='Login')
    passwd = fields.Char(string='Password')
    update = fields.Boolean(string='Update')
    update_rev = fields.Integer(string='Update revision')

    @api.multi
    def button_install(self):
        try:
            if self.update:
                svn_repository_url = '%s/%s/trunk/%s' % (
                self.repository_id and self.repository_id.url or False, self.module_id.technical_name,
                self.module_id.technical_name)
                destination_path = '%s/%s' % (self.env.user.sudo().personal_addons_path, self.module_id.technical_name)
                remote_client = svn.remote.RemoteClient(svn_repository_url, username=self.env.user.sudo().svn_account,
                                                        password=self.env.user.sudo().svn_password)
                if bool(self.update_rev):
                    remote_client.checkout(destination_path, revision=self.update_rev)
                else:
                    remote_client.checkout(destination_path)

                local_svn = svn.local.LocalClient(destination_path, username=self.env.user.sudo().svn_account,
                                                  password=self.env.user.sudo().svn_password)
                local_info = local_svn.info()
                # print 'revision %s checked out' % local_info['commit_revision']


            url = 'http://%s' % self.database_id.name
            common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
            uid = common.authenticate(
                self.database_id.name,
                self.database_id.login,
                self.database_id.passwd,
                {'raise_exception':True})
            _logger.info('SUCCESSFULLY LOGGED IN %s!!!', url)

            models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

            wizard_id = models.execute_kw(self.database_id.name, uid, self.database_id.passwd,
                              'base.module.update', 'create', [{}])
            # _logger.info('CREATED %s SUCCESSFULLY!!!', wizard_id)

            models.execute_kw(self.database_id.name, uid, self.database_id.passwd,
                              'base.module.update', 'update_module', [wizard_id], {})
            _logger.info('MODULE LIST UPDATED SUCCESSFULLY in %s!!!', url)

            module_id = models.execute_kw(self.database_id.name,uid,self.database_id.passwd,
                'ir.module.module', 'search',[
                    [['name', '=', self.module_id.technical_name]]
                ],{'limit': 1})
            # print '*********',module_id


            module_state = models.execute_kw(self.database_id.name, uid, self.database_id.passwd,
                                          'ir.module.module', 'read', module_id, {'fields': ['state']})
            # print '*********', module_state
            _logger.info(module_state)
            if module_state[0]['state'] == 'uninstalled':
                try:
                    # print 'to install'
                    _logger.info('INSTALLING %s in %s...', (self.module_id.technical_name, url))
                    models.execute_kw(self.database_id.name, uid, self.database_id.passwd,
                                  'ir.module.module', 'button_immediate_install', module_id, {})
                    _logger.info('%s SUCCESSFULLY INSTALLED in %s...', (self.module_id.technical_name, url))
                except Exception as ex1:
                    _logger.error(ex1)
                    models.execute_kw(self.database_id.name, uid, self.database_id.passwd,
                                      'ir.module.module', 'button_install_cancel', module_id, {})
            elif module_state[0]['state'] == 'installed':
                try:
                    # print 'to upgrade'
                    _logger.info('UPGRADING %s in %s...', (self.module_id.technical_name, url))
                    models.execute_kw(self.database_id.name, uid, self.database_id.passwd,
                                      'ir.module.module', 'button_immediate_upgrade', module_id, {})
                    _logger.info('%s SUCCESSFULLY UPGRADED in %s...', (self.module_id.technical_name, url))
                except Exception as ex2:
                    _logger.error(ex2)
                    models.execute_kw(self.database_id.name, uid, self.database_id.passwd,
                                      'ir.module.module', 'button_upgrade_cancel', module_id, {})
        except Exception as e:
            # print e
            _logger.error(e)
            raise UserError(e)


class ModuleRevisionReviewWizard(models.TransientModel):
    _name = 'c1_project_dev.module.review.wizard'

    module_id = fields.Many2one('c1_project_dev.module', 'Module')
    user_id = fields.Many2one('res.users', 'User', default=lambda self: self.env.uid)
    date = fields.Datetime('Date', default=fields.Datetime.now)
    revision = fields.Integer('Subversion revision')
    judgement = fields.Selection([('good','OK'),('not_good','NOT OK')], string='Judgement', translate=True)
    description = fields.Text(string='Raison', translate=True)

    @api.multi
    def button_mark(self):
        self.env['c1_project_dev.module.review'].create({
            'module_id': self.module_id and self.module_id.id,
            'user_id': self.env.uid,
            'revision': self.revision,
            'judgement': self.judgement,
            'description': self.description,
        })
        return {'type':'ir.actions.act_window.close'}


class ModuleCopyWizard(models.TransientModel):
    _name = 'c1_project_dev.module.copy.wizard'

    @api.multi
    def button_copy_module(self):
        container = self.env.user.sudo().docker_instance_id
        if self.module_id.repository_id:
            moved = False
            target = os.path.join(self.module_id.repository_id.system_path or '', self.module_id.technical_name)
            destination = os.path.join(self.env.user.sudo().personal_addons_path or '', self.module_id.technical_name)
            try:
                if container:
                    container.action_stop();

                if os.path.exists(destination):
                    shutil.move(destination, destination+'.bak')
                    moved = True

                shutil.copytree(target, destination)

                if moved:
                    shutil.rmtree(destination+'.bak')


                if container:
                    container.action_start();

            except Exception as e:
                _logger.exception(e)
                if moved:
                    shutil.rmtree(destination+'.bak')

                if container:
                    container.action_start();

                raise UserError(e)


            if self.env.context.get('refresh_ui'):
                return {
                    'type': 'ir.actions.client',
                    'tag': 'reload',
                    'params': {
                        'wait': True,
                    },
                }
        return

    module_id = fields.Many2one('c1_project_dev.module', 'Module')


class ModuleDeploymentWizard(models.TransientModel):
    _name = 'c1_project_dev.module.deployment.wizard'


    @api.multi
    def button_deploy(self):
        container = self.env.user.sudo().docker_instance_id
        if self.module_id.repository_id:
            moved = False
            target = os.path.join(self.module_id.repository_id.system_path or '', self.module_id.technical_name)
            destination = os.path.join(self.server_id.addons_path or '', self.module_id.technical_name)
            try:
                if container:
                    container.action_stop();

                if os.path.exists(destination):
                    shutil.move(destination, destination + '.bak')
                    moved = True

                shutil.copytree(target, destination)

                if self.task_id:
                    self.task_id.with_context({'action_deploy' : True}).write({
                        'stage_id': self.env['ir.model.data'].xmlid_to_res_id('c1_project_dev.done')
                    })

                if moved:
                    shutil.rmtree(destination + '.bak')

                if container:
                    container.action_start();

            except Exception as e:
                _logger.exception(e)
                if moved:
                    shutil.rmtree(destination + '.bak')

                if container:
                    container.action_start();

                raise UserError(e)
            if self.env.context.get('refresh_ui'):
                return {
                    'type': 'ir.actions.client',
                    'tag': 'reload',
                    'params': {
                        'wait': True,
                    },
                }
        return

    @api.onchange('server_id')
    def _onchange_server_id(self):
        client = docker.from_env()
        for rec in self:
            if rec.server_id.container_id:
                c = client.containers.get(rec.server_id.container_id.name)
                output = c.exec_run('pip list --format=json')
                _logger.warning(output)

    @api.multi
    def _compute_installable(self):
        client = docker.from_env()
        for rec in self:
            if rec.server_id.container_id:
                try:
                    c = client.containers.get(rec.server_id.container_id.name)
                    output = c.exec_run('pip list --format=json')
                    installed_packages = ast.literal_eval(output)
                    package_names = [ p['name'] for p in installed_packages ]

                    deps = rec.module_id.python_dependencies or ''
                    deps = deps.strip()
                    deps = deps.split(',')

                    can_install = True
                    for d in deps:
                        if d not in package_names:
                            can_install = False
                            break

                    rec.installable = can_install
                    _logger.warning(output)
                except Exception as e:
                    rec.installable = False



    server_id = fields.Many2one('c1_project_dev.server', string='Server', required=True)
    module_id = fields.Many2one('c1_project_dev.module', string='Module')
    task_id = fields.Many2one('project.task', string='Task')
    # current_downloaded_rev = fields.Integer(string='Downloaded revision', related='module_id.current_downloaded_rev')
    # on_server_rev = fields.Integer(string='Revision on server', compute='_compute_on_server_rev')
    on_server_rev = fields.Integer(string='Revision on server', related='module_id.onserver_revision', readonly=True)
    python_dependencies = fields.Char(string='Python package requirement', related='module_id.python_dependencies', readonly=True)
    installable = fields.Boolean(string='Installable')
