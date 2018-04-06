# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import xmlrpc.client
import logging

import os

import shutil

import datetime
from operator import attrgetter

import svn

_logger = logging.getLogger(__name__)

import odoo
from odoo import api, fields, models, tools, SUPERUSER_ID, _
from odoo.exceptions import UserError, ValidationError, AccessError, AccessDenied


class Users(models.Model):
    _inherit = 'res.users'

    def __init__(self, pool, cr):
        super(Users, self).SELF_WRITEABLE_FIELDS.append('svn_account')
        super(Users, self).SELF_READABLE_FIELDS.append('svn_account')
        super(Users, self).SELF_WRITEABLE_FIELDS.append('svn_password')
        super(Users, self).SELF_READABLE_FIELDS.append('svn_password')
        super(Users, self).SELF_READABLE_FIELDS.append('is_svn_user')
        super(Users, self).SELF_READABLE_FIELDS.append('related_database')

    @api.multi
    def preference_change_svn_credentials(self):
        return {
            'type':'ir.actions.act_window',
            'res_model':'res.users.svn.wizard',
            'view_mode':'form',
            'view_type':'form',
            'target':'new',
        }

    @api.model
    def get_users_backupspath_content(self):
        backup_dir = os.path.join(self.env.user.sudo().personal_data_path or '', 'backups')
        folders = [ f for f in os.listdir(backup_dir) if os.path.isdir(os.path.join(backup_dir, f))]
        return folders

    @api.model
    def get_backupspath_subfolder_content(self, subfolder, reverse = False):
        # print '>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>', subfolder, reverse
        subfolder_path = os.path.join(self.env.user.sudo().personal_data_path or '', 'backups', subfolder)
        file_list = [os.path.normcase(f) for f in os.listdir(subfolder_path) if os.path.isfile(os.path.join(subfolder_path, f))]

        class BackupFile:
            def __init__(self, base_name, full_name, date):
                self.base_name = base_name
                self.full_name = full_name
                self.date = date

        list = []
        for f in file_list:
            f_data = f.split('.', 1)
            # base_name = f[1]
            date_str = f_data[0]
            date = datetime.datetime.strptime(date_str, '%Y_%m_%d_%H_%M_%S')
            list.append(BackupFile(base_name=f, date=date, full_name=os.path.join(subfolder_path, f)))

        # print sorted(list, key=attrgetter('base_name', 'date'), reverse=True)

        _logger.info(file_list)
        return [ l.base_name for l in sorted(list, key=attrgetter('date'), reverse=reverse)]

    @api.model
    def delete_backup_file(self, subfolder, filename):
        filepath = os.path.join(self.env.user.sudo().personal_data_path or '', 'backups', subfolder, filename)
        os.remove(filepath)

    @api.model
    def delete_backup_folder(self, subfolder):
        filepath = os.path.join(self.env.user.sudo().personal_data_path or '', 'backups', subfolder)
        shutil.rmtree(filepath)


    svn_account_id = fields.Many2one('c1_project_dev.svn_account', string='Svn account')
    svn_account = fields.Char(string='SVN account', related='svn_account_id.svn_account', copy=False)
    svn_password = fields.Char(string='SVN password', related='svn_account_id.svn_password', copy=False)

    is_svn_user = fields.Boolean(string='Is SVN user', copy=False)
    related_database = fields.Char(string='Related database', copy=False)
    related_database_ids = fields.One2many('c1_project_dev.userdb.info', 'user_id', string='Related databases', copy=False)

    docker_instance = fields.Char(string='Docker container name or ID', translate=True)
    docker_user = fields.Char(string='Docker user', translate=True)
    docker_user_psswd = fields.Char(string='Docker user password', translate=True)

    docker_instance_id = fields.Many2one('c1_project_dev.docker.container', string='Docker container')

    docker_db_suffix = fields.Char(string='Database suffix', related='docker_instance_id.docker_db_suffix')

    path_id = fields.Many2one('c1_project_dev.users.path', string='Personal directory')
    personal_addons_path = fields.Char(string='Addons path', related='docker_instance_id.addons_path')
    personal_log_path = fields.Char(string='Log path', related='docker_instance_id.log_path')
    personal_data_path = fields.Char(string='Data path', related='docker_instance_id.data_path')
    personal_enterprise_addons_path = fields.Char(string='Enterprise addons path', related='docker_instance_id.enterprise_addons_path')



class UserDatabaseModuleInfo(models.Model):
    _name = 'c1_project_dev.module.info'
    _order = 'name'

    STATES = [
        ('uninstallable', 'Uninstallable'),
        ('uninstalled', 'Not Installed'),
        ('installed', 'Installed'),
        ('to upgrade', 'To be upgraded'),
        ('to remove', 'To be removed'),
        ('to install', 'To be installed'),
    ]

    @api.model
    def search(self, args=[], offset=0, limit=0, order=None, count=False):
        # print self.env.context
        if self.env.context.get('db_id', 0) > 0:
            args.append( ('database_id','=', self.env.context.get('db_id')) )
        return super(UserDatabaseModuleInfo, self).search(args=args, offset=offset, limit=limit, order=order, count=count)

    def button_install(self):
        # print self.env.context
        # self.name

        try:
            if self.onserver_rev > self.current_rev:
                m = self.env['c1_project_dev.module'].sudo().search([('technical_name', '=', self.name)], limit=1)
                if m:
                    svn_repository_url = '%s/%s/trunk/%s' % (
                        m.repository_id and m.repository_id.url or False, m.technical_name,
                        m.technical_name)
                    destination_path = '%s/%s' % (self.env.user.sudo().personal_addons_path, m.technical_name)
                    remote_client = svn.remote.RemoteClient(svn_repository_url, username=m.repository_id.username,
                                                            password=m.repository_id.passwd)
                    remote_client.checkout(destination_path)
                    local_svn = svn.local.LocalClient(destination_path)
                    local_info = local_svn.info()
                    # print 'revision %s checked out' % local_info['commit_revision']

                    # self.env.user.sudo().docker_instance_id.action_restart()
                    # while self.env.user.sudo().docker_instance_id.state != 'running':
                    #     pass

            url = 'http://%s' % self.database_id.name
            common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
            uid = common.authenticate(
                self.database_id.name,
                self.database_id.login,
                self.database_id.passwd,
                {'raise_exception': True})
            _logger.info('SUCCESSFULLY LOGGED IN %s!!!', url)

            models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

            # wizard_id = models.execute_kw(self.database_id.name, uid, self.database_id.passwd,
            #                               'base.module.update', 'create', [{}])
            # # _logger.info('CREATED %s SUCCESSFULLY!!!', wizard_id)
            #
            # models.execute_kw(self.database_id.name, uid, self.database_id.passwd,
            #                   'base.module.update', 'update_module', [wizard_id], {})
            _logger.info('MODULE LIST UPDATED SUCCESSFULLY in %s!!!', url)

            module_id = models.execute_kw(self.database_id.name, uid, self.database_id.passwd,
                                          'ir.module.module', 'search', [[['name', '=', self.name]]], {'limit': 1})
            # print '*********', module_id
            try:
                _logger.info('INSTALLING %s in %s...', self.name, url)
                models.execute_kw(self.database_id.name, uid, self.database_id.passwd,
                                  'ir.module.module', 'button_immediate_install', module_id, {})
                _logger.info('%s SUCCESSFULLY INSTALLED in %s...', self.name, url)
            except Exception as ex1:
                models.execute_kw(self.database_id.name, uid, self.database_id.passwd,
                                  'ir.module.module', 'button_install_cancel', module_id, {})
        except Exception as e:
            _logger.error(e)
            raise UserError(e)

        db_id = self.database_id.id
        # self.database_id.get_db_info()
        # if(self.env.context.get('from_tree_view') or self.env.context.get('from_kanban_view')):
        #     print self.env.context
        #     # action = self.env.ref('c1_project_dev.action_database_management').read()
        #     print '***********************'
        #     return {
        #         'type':'ir.actions.act_window',
        #         'res_model':'c1_project_dev.userdb.info',
        #         'views': [[False, "form"]],
        #         'res_id': db_id,
        #         'target': 'main'
        #     }
        # return True
        return self.database_id.with_context(refresh_ui=True).get_db_info()

    def button_uninstall(self):
        try:
            url = 'http://%s' % self.database_id.name
            common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
            uid = common.authenticate(
                    self.database_id.name,
                    self.database_id.login,
                    self.database_id.passwd,
            {'raise_exception': True})
            _logger.info('SUCCESSFULLY LOGGED IN!!!')

            models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
            module_id = models.execute_kw(self.database_id.name, uid, self.database_id.passwd,
                                              'ir.module.module', 'search', [
                                                  [['name', '=', self.name]]
                                              ], {'limit': 1})
            # print '*********', module_id
            try:
                models.execute_kw(self.database_id.name, uid, self.database_id.passwd,
                                  'ir.module.module', 'button_immediate_uninstall', module_id, {})
            except Exception as ex1:
                models.execute_kw(self.database_id.name, uid, self.database_id.passwd,
                                  'ir.module.module', 'button_uninstall_cancel', module_id, {})
        except Exception as e:
            _logger.error(e)
            raise UserError(e)

        db_id = self.database_id.id
        # self.database_id.get_db_info()
        # if (self.env.context.get('from_tree_view') or self.env.context.get('from_kanban_view')):
        #     print self.env.context
        #     # action = self.env.ref('c1_project_dev.action_database_management').read()
        #     print '***********************'
        #     return {
        #         'type': 'ir.actions.act_window',
        #         'res_model': 'c1_project_dev.userdb.info',
        #         'views': [[False, "form"]],
        #         'res_id': db_id,
        #         'target': 'main'
        #     }
        # return True
        return self.database_id.with_context(refresh_ui=True).get_db_info()

    def button_upgrade(self):
        try:
            if self.onserver_rev > self.current_rev:
                m = self.env['c1_project_dev.module'].sudo().search([('technical_name', '=', self.name)], limit=1)
                if m:
                    svn_repository_url = '%s/%s/trunk/%s' % (
                        m.repository_id and m.repository_id.url or False, m.technical_name,
                        m.technical_name)
                    destination_path = '%s/%s' % (self.env.user.sudo().personal_addons_path, m.technical_name)
                    remote_client = svn.remote.RemoteClient(svn_repository_url, username=m.repository_id.username,
                                                            password=m.repository_id.passwd)
                    remote_client.checkout(destination_path)
                    local_svn = svn.local.LocalClient(destination_path)
                    local_info = local_svn.info()
                    # print 'revision %s checked out' % local_info['commit_revision']

                    # self.env.user.sudo().docker_instance_id.action_restart()
                    # while self.env.user.sudo().docker_instance_id.state != 'running':
                    #     pass

            url = 'http://%s' % self.database_id.name
            common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
            uid = common.authenticate(
                    self.database_id.name,
                    self.database_id.login,
                    self.database_id.passwd,
                    {'raise_exception': True})
            _logger.info('SUCCESSFULLY LOGGED IN!!!')

            models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
            module_id = models.execute_kw(self.database_id.name, uid, self.database_id.passwd,
                                              'ir.module.module', 'search', [
                                                  [['name', '=', self.name]]
                                              ], {'limit': 1})
            # print '*********', module_id
            try:
                models.execute_kw(self.database_id.name, uid, self.database_id.passwd,
                                  'ir.module.module', 'button_immediate_upgrade', module_id, {})
            except Exception as ex1:
                models.execute_kw(self.database_id.name, uid, self.database_id.passwd,
                                  'ir.module.module', 'button_upgrade_cancel', module_id, {})
        except Exception as e:
            _logger.error(e)
            raise UserError(e)

        db_id = self.database_id.id
        # self.database_id.get_db_info()
        # if (self.env.context.get('from_tree_view') or self.env.context.get('from_kanban_view')):
        #     print self.env.context
        #     # action = self.env.ref('c1_project_dev.action_database_management').read()
        #     print '***********************'
        #     return {
        #         'type': 'ir.actions.act_window',
        #         'res_model': 'c1_project_dev.userdb.info',
        #         'views': [[False, "form"]],
        #         'res_id': db_id,
        #         'target': 'main'
        #     }
        #
        # return True
        return self.database_id.with_context(refresh_ui=True).get_db_info()

    def button_cancel_install(self):
        try:
            url = 'http://%s' % self.database_id.name
            common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
            uid = common.authenticate(
                    self.database_id.name,
                    self.database_id.login,
                    self.database_id.passwd,
                    {'raise_exception': True})
            _logger.info('SUCCESSFULLY LOGGED IN!!!')

            models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
            module_id = models.execute_kw(self.database_id.name, uid, self.database_id.passwd,
                                              'ir.module.module', 'search', [
                                                  [['name', '=', self.name]]
                                              ], {'limit': 1})
            # print '*********', module_id
            models.execute_kw(self.database_id.name, uid, self.database_id.passwd,
                                  'ir.module.module', 'button_install_cancel', module_id, {})
        except Exception as e:
            _logger.error(e)
            raise UserError(e)

        db_id = self.database_id.id
        # self.database_id.get_db_info()
        # if (self.env.context.get('from_tree_view') or self.env.context.get('from_kanban_view')):
        #     print self.env.context
        #     # action = self.env.ref('c1_project_dev.action_database_management').read()
        #     print '***********************'
        #     return {
        #         'type': 'ir.actions.act_window',
        #         'res_model': 'c1_project_dev.userdb.info',
        #         'views': [[False, "form"]],
        #         'res_id': db_id,
        #         'target': 'main'
        #     }
        #
        # return True
        return self.database_id.with_context(refresh_ui=True).get_db_info()

    def button_cancel_upgrade(self):
        try:
            url = 'http://%s' % self.database_id.name
            common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
            uid = common.authenticate(
                    self.database_id.name,
                    self.database_id.login,
                    self.database_id.passwd,
                    {'raise_exception': True})
            _logger.info('SUCCESSFULLY LOGGED IN!!!')

            models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
            module_id = models.execute_kw(self.database_id.name, uid, self.database_id.passwd,
                                              'ir.module.module', 'search', [
                                                  [['name', '=', self.name]]
                                              ], {'limit': 1})
            # print '*********', module_id
            models.execute_kw(self.database_id.name, uid, self.database_id.passwd,
                                  'ir.module.module', 'button_upgrade_cancel', module_id, {})
        except Exception as e:
            _logger.error(e)
            raise UserError(e)

        db_id = self.database_id.id
        # self.database_id.get_db_info()
        # if (self.env.context.get('from_tree_view') or self.env.context.get('from_kanban_view')):
        #     print self.env.context
        #     # action = self.env.ref('c1_project_dev.action_database_management').read()
        #     print '***********************'
        #     return {
        #         'type': 'ir.actions.act_window',
        #         'res_model': 'c1_project_dev.userdb.info',
        #         'views': [[False, "form"]],
        #         'res_id': db_id,
        #         'target': 'main'
        #     }
        #
        # return True
        return self.database_id.with_context(refresh_ui=True).get_db_info()

    def button_cancel_uninstall(self):
        try:
            url = 'http://%s' % self.database_id.name
            common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
            uid = common.authenticate(
                self.database_id.name,
                    self.database_id.login,
                    self.database_id.passwd,
                    {'raise_exception': True})
            _logger.info('SUCCESSFULLY LOGGED IN!!!')

            models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
            module_id = models.execute_kw(self.database_id.name, uid, self.database_id.passwd,
                                              'ir.module.module', 'search', [
                                                  [['name', '=', self.name]]
                                              ], {'limit': 1})
            # print '*********', module_id
            models.execute_kw(self.database_id.name, uid, self.database_id.passwd,
                                  'ir.module.module', 'button_uninstall_cancel', module_id, {})
        except Exception as e:
            _logger.error(e)
            raise UserError(e)

        db_id = self.database_id.id

        # if (self.env.context.get('from_tree_view') or self.env.context.get('from_kanban_view')):
        #     print self.env.context
        #     # action = self.env.ref('c1_project_dev.action_database_management').read()
        #     print '***********************'
        #     return {
        #         'type': 'ir.actions.act_window',
        #         'res_model': 'c1_project_dev.userdb.info',
        #         'views': [[False, "form"]],
        #         'res_id': db_id,
        #         'target': 'main'
        #     }

        return self.database_id.with_context(refresh_ui=True).get_db_info()

    name = fields.Char(string='Technical name', translate=True)
    shortdesc = fields.Char(string='Short description', translate=True)
    state = fields.Selection(string='State', selection=STATES, translate=True)
    database_id = fields.Many2one('c1_project_dev.userdb.info')
    local_module_record = fields.Many2one('c1_project_dev.module')
    current_rev = fields.Integer(related='local_module_record.current_downloaded_rev', string='Current revision', default=-1)
    onserver_rev = fields.Integer(related='local_module_record.onserver_revision', string='Server revision', default=-1)



class UserDatabaseInfo(models.Model):
    _name = 'c1_project_dev.userdb.info'
    _order = 'name'

    def button_install(self):
        if self.module_search_id:
            module = self.module_search_id
            self.module_search_id = False
            return module.with_context(from_tree_view=True).button_install()
        return False

    def button_uninstall(self):
        if self.module_search_id:
            module = self.module_search_id
            self.module_search_id = False
            return module.with_context(from_tree_view=True).button_uninstall()
        return False

    def button_upgrade(self):
        if self.module_search_id:
            module = self.module_search_id
            self.module_search_id = False
            return module.with_context(from_tree_view=True).button_upgrade()
        return False

    def button_cancel_install(self):
        if self.module_search_id:
            module = self.module_search_id
            self.module_search_id = False
            return module.with_context(from_tree_view=True).button_cancel_install()
        return False

    def button_cancel_upgrade(self):
        if self.module_search_id:
            module = self.module_search_id
            self.module_search_id = False
            return module.with_context(from_tree_view=True).button_cancel_upgrade()
        return False

    def button_cancel_uninstall(self):
        if self.module_search_id:
            module = self.module_search_id
            self.module_search_id = False
            return module.with_context(from_tree_view=True).button_cancel_uninstall()
        return False

    @api.multi
    def button_goto(self):
        url = 'http://%s/web' % self.name
        return {
            'type':'ir.actions.act_url',
            'url': url,
            'target':'new'
        }

    @api.multi
    def button_backup(self):
        return self.env['c1_project_dev.database.wizard'].create({
            'database_info_id': self.id,
            'action': 'maintain'
        }).button_backup_database()

    @api.multi
    def get_db_info(self):
        for record in self:
            try:
                url = 'http://%s' % record.name
                common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
                uid = common.authenticate(record.name, record.login, record.passwd,{'raise_exception': True})
                _logger.warning('####SUCCESSFULLY LOGGED IN!!!')


                models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
                wzd = models.execute_kw(record.name, uid, record.passwd,
                                  'base.module.update', 'create', [{}])

                models.execute_kw(record.name, uid, record.passwd,
                                  'base.module.update', 'update_module', [wzd])


                # models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
                modules = models.execute_kw(record.name, uid, record.passwd,
                    'ir.module.module', 'search_read', [[['id', '!=', False]]], {'fields': ['name','shortdesc','state']})

                record.installed_modules.unlink()

                # mods = [self.env['c1_project_dev.module.info'].sudo().create({
                #     'database_id':record.id,
                #     'name':mod['name'],
                #     'state':mod['state'],
                #     'shortdesc':mod['shortdesc'],
                # }).id for mod in modules]
                # _logger.info(mods)

                for mod in modules:
                    lm = self.env['c1_project_dev.module'].sudo().search([('technical_name', '=', mod['name'])], limit=1)
                    data = {
                        'database_id': record.id,
                        'name': mod['name'],
                        'state': mod['state'],
                        'shortdesc': mod['shortdesc'],
                        'local_module_record': lm and lm.id or False
                    }
                    self.env['c1_project_dev.module.info'].sudo().create(data)

                # for m in mods:
                #     lm = self.env['c1_project_dev.module'].sudo().search(
                #         [('technical_name', '=', mod['name'])], limit=1)
                #     if lm:
                #         m.sudo().write({'local_module_record': lm.id})

                # _logger.info(mods)
                # record.installed_modules = (6, _, mods)
            except Exception as e:
                raise UserError(e)
                _logger.error(e)
                pass
        if self.env.context.get('refresh_ui'):
            menu = self.env.ref('c1_project_dev.menu_databses_info')
            action = self.env.ref('c1_project_dev.action_database_management')
            # return action
            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
                'params': {
                    'wait': True,
                    # 'menu_id': menu and menu.id or False,
                    # 'res_id': self.id,
                    # 'view_type': 'form',
                    # 'model': self._name,
                    # 'action':action and action.id or False,
                },
            }

    @api.multi
    def button_filter(self):
        return {
            'type': 'ir.actions.client',
            'tag': 'c1_project_dev.module_filter',
            'params': {
                'wait': True,
            },
        }



    @api.model
    def search(self, args=[], offset=0, limit=None, order=None, count=False):
        if not self.env.user.sudo().has_group('base.group_system'):
            args.append(('user_ids','=',self.env.uid))
        return super(UserDatabaseInfo, self).search(args, offset, limit, order, count)


    @api.multi
    def write(self, values):
        if len(set(['user_id','user_ids','login','passwd']).intersection(set(values.keys()))) >= 1:
            if not self.env.user.sudo().has_group('base.group_system') and self.env.user not in [self.user_ids]:
                raise AccessError(_('You are not allowed to perform this operation. contact your administrator if you think this is an error.'))
        return super(UserDatabaseInfo, self).write(values)

    @api.one
    def unlink(self):
        # if self.env.user != self.user_id and not self.env.user.has_group('base.group_system'):
        if self.env.user not in  self.user_ids and not self.env.user.sudo().has_group('base.group_system'):
            raise AccessError(_(
                'You are not allowed to perform this operation. contact your administrator if you think this is an error.'))
        data_path =  os.path.join(self.env.user.sudo().personal_data_path or '', 'filestore', self.name)
        res = super(UserDatabaseInfo, self).unlink()
        if os.path.exists(data_path):
            shutil.rmtree(data_path)
        return res


    def _compute_is_local(self):
        for rec in self:
            rec.is_local = odoo.service.db.exp_db_exist(rec.name)

    name = fields.Char(string='Database name', translate=True)
    login = fields.Char(string='Login')
    passwd = fields.Char(string='Password')
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.uid)
    user_ids = fields.Many2many('res.users', string='Users', default=lambda self: [self.env.uid])
    installed_modules = fields.One2many('c1_project_dev.module.info', 'database_id', string='Installed modules')
    # module_search_id = fields.Many2one('c1_project_dev.module.info',  string='Module')
    # module_search_state = fields.Selection(related='module_search_id.state',  string='search module state')
    is_local = fields.Boolean('Local', compute='_compute_is_local')

    _sql_constraints = [
        ('unique_name', 'UNIQUE(name, login)', 'The combination of the database name and the login should be unique')
    ]



class ChangeSVNCredentials(models.TransientModel):
    _name = 'res.users.svn.wizard'
    _order = 'name'

    current_user_password = fields.Char(string='Password', required=True)
    svn_account = fields.Char(string='SVN account', required=True, default=lambda self: self.env.user.svn_account)
    svn_password = fields.Char(string='SVN account password', required=True)

    @api.multi
    def change_svn_credentials(self):
        self.env['res.users'].sudo().check(self._cr.dbname, self._uid, self.current_user_password)
        self.env.user.sudo().write({
            'svn_account': self.svn_account,
            'svn_password': self.svn_password
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'reload_context',
        }

