# -*- coding: utf-8 -*-
import base64
import datetime
import glob
import xmlrpc.client
import zipfile
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
from contextlib import closing

import odoo
import psycopg2
import svn
from svn.exception import SvnException
import svn.common
import svn.remote
import svn.local
from odoo import api, fields, models, tools, SUPERUSER_ID, _
from odoo.exceptions import UserError, ValidationError
from operator import itemgetter, attrgetter, methodcaller
from odoo.tools.safe_eval import safe_eval
from odoo.tools import pycompat
import subprocess
import os
import pip
# import pysftp
import logging

_logger = logging.getLogger(__name__)


class DatabaseManagementWizard(models.TransientModel):
    _name = 'c1_project_dev.database.wizard'

    DBNAME_PATTERN = '^[a-zA-Z0-9][a-zA-Z0-9.-]+$'

    # def __init__(self, pool, cr):
    #     print '====',odoo.service.db.exp_list_lang()
    #     print '====',odoo.service.db.exp_list_countries()
    #     setattr(self.database_info_id, 'domain',
    #       [('user_id','=', self.env.uid)])

    def _default_backup_file(self):
        self.env['c1_project_dev.backup_file'].collect_files()
        self.env['c1_project_dev.backup_file'].collect_personal_files()
        return

    @api.multi
    def _default_user_db_suffix(self):
        return self.env.user.sudo().docker_db_suffix

    # def _default_user_database(self):
    #     return (self.env.user.mapped('related_database_ids.name'))
    #             and self.env.user.mapped('related_database_ids.name')[0] or False

    @api.onchange('recovery_type')
    def _onchange_recovery_type(self):
        self.db_project_record = False
        self.server = False
        self.database_record_id = False
        self.db_backup_file = False

    @api.onchange('server')
    def _onchange_server(self):
        return {
            'domain':{
                'db_project_record': [('type','=','folder'),('source','=','production'),('project_folder','=',self.server)]
            },
        }

    @api.onchange('db_project_record')
    def _onchange_project(self):
        return {
            'domain': {
                'db_backup_file': [('type','=','file'),('source','=','production'),('project_folder', '=', self.db_project_record and self.db_project_record.name or '')]
            },
        }

    @api.onchange('database_record_id')
    def _onchange_database_record_id(self):
        self.db_backup_file = False
        return {
            'domain': {
                'db_backup_file': [('type','=','file'), ('source','=','user'), ('database', '=', self.database_record_id and self.database_record_id.name or '')]
            },
        }

    db_name = fields.Char(string='Database', translate = True)
    login = fields.Char(string='Login', translate = True)
    login_restore = fields.Char(string='Login', translate = True)
    passwd = fields.Char(string='Password', translate = True)
    passwd_restore = fields.Char(string='Password', translate = True)
    lang = fields.Selection(string='Language',
                            # default = 'zh_CN',
                            default = 'en_US',
                            selection = odoo.service.db.exp_list_lang(), translate = True)
    country = fields.Selection(string='Country',
                               default = 'cn',
                               selection = odoo.service.db.exp_list_countries(), translate = True)
    demo = fields.Boolean(string='Install Demo', translate = True)
    database_info_id = fields.Many2one('c1_project_dev.userdb.info',
                                       # domain = [('user_id','=',lambda self: self.user_id and self.user_id.id or False)],
                                       string='Database')
    delete_backup_files = fields.Boolean(string='Delete related backup files')
    database_record_id = fields.Many2one('c1_project_dev.backup_file',
                                       # domain = [('user_id','=',lambda self: self.user_id and self.user_id.id or False)],
                                       string='Database')


    user_database = fields.Char(string='Database name', translate = True)
    # user_database_suffix = fields.Char(string='User database suffix', default=lambda self: self._default_user_db_suffix())
    # user_database_suffix_cp = fields.Char(string='User database suffix', default=lambda self: self._default_user_db_suffix())
    # user_database_suffix_res = fields.Char(string='User database suffix', default=lambda self: self._default_user_db_suffix())


    backup_db_name = fields.Char(string='Database name', translate = True)
    db_copy_name = fields.Char(string='Database name', translate = True)
    action = fields.Selection(string='Backup from', selection=[
        ('create','Create new database'),
        ('maintain','Delete or copy database'),
        ('restore', 'Restore')], default='create', translate = True)
    # perso_db_backup_file = fields.Selection(string='Database backup file', selection=lambda self:self._get_backup_files_selection(),translate = True)
    # perso_db_backup_file = fields.Many2one('c1_project_dev.backup_file', string='Database backup file', selection=lambda self:self._get_backup_files_selection(),translate = True)
    # db_backup_file = fields.Selection(string='Database backup file', selection=lambda self:self._get_backup_files_selection(),translate = True)
    db_backup_file = fields.Many2one('c1_project_dev.backup_file', string='Database backup file', ondelete='set null', default=lambda self:self._default_backup_file(),translate = True)
    db_project_record = fields.Many2one('c1_project_dev.backup_file', string='Project', ondelete='set null', default=lambda self:self._default_backup_file(),translate = True)
    server = fields.Selection(string='Server', selection=lambda self:self._get_servers_selection(), translate = True)
    recovery_type = fields.Selection(string='recovery type', selection=[('production_server','From production server'), ('personal_path','From personal path')], translate = True)


    def _get_backup_files_selection(self):
        try:
            # backup_path = os.path.join(self.env.user.sudo().personal_data_path, 'backups')
            # fileList = [ (os.path.normcase(f), os.path.normcase(f)) for f in os.listdir(backup_path)
            #              if (os.path.isfile(os.path.join(backup_path, f)) and os.path.splitext(os.path.normcase(f))[1] == '.zip') ]
            file_list = [ (f, os.path.basename(f)) for f in glob.glob('/data/saas/loc/*/data/backups/*.zip') ]

            class BackupFile:
                def __init__(self, base_name, full_name, date):
                    self.base_name = base_name
                    self.full_name = full_name
                    self.date = date

            list = []
            for f in file_list:
                f_data = f[1].split('_', 1)
                base_name = f[1]
                date_str = f_data[1].split('.')[0]
                date = datetime.datetime.strptime(date_str, '%Y-%m-%d_%H-%M-%S')
                list.append( BackupFile(base_name=base_name, date=date, full_name=f[0]) )

            # print sorted(list, key=attrgetter('base_name', 'date'), reverse=True)


            _logger.info(file_list)
            return [(l.full_name, l.base_name)for l in sorted(list, key=attrgetter('base_name', 'date'), reverse=True)]
        except Exception as e:
            _logger.error(e.message)
        return []

    def _get_servers_selection(self):
        try:
            backup_path = self.env['res.config.settings'].sudo().get_values().get('db_backup_dir')
            servers = [(f, f) for f in os.listdir(backup_path) if os.path.isdir(os.path.join(backup_path, f))]
            return servers
        except Exception as e:
            _logger.exception(e)
        return []


    # sftp_file_absolute_path = fields.Char(string='File\'s absolute path on Server', translate = True)
    # sftp_host = fields.Char(string='SFTP Server',
    #                         help="The host name or IP address from your remote server. For example 192.168.0.1"
    #                         ,translate = True)
    # sftp_port = fields.Integer(string="SFTP Port",
    #                            default=22,help="The port on the FTP server that accepts SSH/SFTP calls.")
    # sftp_user = fields.Char(string='Username in the SFTP Server',
    #                         help="The username where the SFTP connection should be made with. This is the user on the external server.")
    # sftp_password = fields.Char(string="SFTP Password",
    #                             help="The password for the SFTP connection. If you specify a private key file, then this is the password to decrypt it.")
    # sftp_private_key = fields.Char(string="Private key location",
    #                                help="Path to the private key file. Only the Odoo user should have read permissions for that file.")


    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        result = super(DatabaseManagementWizard, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)

        if view_type == 'form':
            doc = etree.XML(result['arch'])
            for node in doc.xpath("//field[@name='database_info_id']"):
                node.set('domain', repr([('user_ids','=',self.env.uid)]))

            fields = ['db_name', 'db_copy_name', 'backup_db_name']
            for field in fields:
                for node in doc.xpath("//field[@name='%s']" % field):
                    node.set('class', 'oe_inline')
                    node.addnext(etree.Element('label', {'string': '.%s' % self.env.user.sudo().docker_db_suffix}))

            result['arch'] = etree.tostring(doc)
        return result

    @api.onchange('database_info_id')
    def _onchange_database_info_id(self):
        ts = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
        for rec in self:
            if rec.database_info_id:
                # suffix_start_idx = rec.database_info_id.name.find(
                #     self.env.user.sudo().docker_db_suffix
                # )
                # suffix_start_idx = suffix_start_idx -1 # to exclude the dot
                # rec.db_copy_name = '%s_%s' % (rec.database_info_id.name[:suffix_start_idx], ts)
                rec.db_copy_name = '%s-%s' % (rec.database_info_id.name.replace('.', '-'), ts)
            else:
                rec.db_copy_name = ''


    def _check_db_name(self, name):
        if not re.match(self.DBNAME_PATTERN, name):
            # _logger.error("DB CHECK NAME NOT passed...")
            raise Exception(
                _('Invalid database name. Only alphanumerical characters, hyphen and dot are allowed.'))

    @api.multi
    def button_create_database(self):
        admin_passwd = odoo.tools.config['admin_passwd']
        info = False
        db_name = False
        try:
            db_name = '%s.%s' % (self.db_name, self.env.user.sudo().docker_db_suffix)
            self._check_db_name(db_name)

            result = odoo.service.db.exp_create_database(
                db_name = db_name, demo = self.demo,
                lang = self.lang, user_password=self.passwd, login=self.login,
                country_code = self.country)
            if not result:
                raise UserError(_('The database %s could not be created') % db_name)

            _logger.info('>>>>>FILESTORE: %s',os.path.dirname(self.env['ir.attachment'].sudo()._filestore()))

            _logger.info('>>>>>EXIST: %s', os.path.exists( os.path.join(os.path.dirname(self.env['ir.attachment'].sudo()._filestore()), db_name) ))
            if os.path.exists( os.path.join(os.path.dirname(self.env['ir.attachment'].sudo()._filestore()), db_name) ):
                shutil.rmtree( os.path.join(os.path.dirname(self.env['ir.attachment'].sudo()._filestore()), db_name) )
            # shutil.move(os.path.join(self.env['ir.attachment'].sudo()._filestore(), db_name),
            #             os.path.join(self.env.user.sudo().personal_data_path, 'filestore'))

            # self.env.user.sudo().related_database_ids.unlink()
            info = self.env['c1_project_dev.userdb.info'].create({
                'name': db_name,
                'login': self.login,
                'passwd': self.passwd,
                'user_id': self.env.uid,
                'user_ids': [(6, 0, [self.env.uid])],
            })
            # if info:
            #     self.env.user.sudo().write({'related_database':info.name})
        except Exception as e:

            if odoo.service.db.exp_db_exist(db_name):
                odoo.service.db.exp_drop(db_name)
            if info:
                info.unlink()

            raise UserError(e)
        return True

    @api.multi
    def button_backup_database(self):
        try:
            # ts = datetime.datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")
            ts = datetime.datetime.utcnow().strftime("%Y_%m_%d_%H_%M_%S")
            backup_format = 'zip'
            # filename = "%s_%s.%s" % (self.database_info_id.name, ts, backup_format)
            filename = "%s.dump.%s" % (ts, backup_format)
            data = odoo.service.db.exp_dump(self.database_info_id.name, backup_format)
            # _logger.info(data)
            # data = data.decode('base64')
            # backup_path = self.env['ct_project.config.settings'].get_value('db_backup_dir') or ''
            backup_path = os.path.join(self.env.user.sudo().personal_data_path, 'backups', self.database_info_id.name)
            if not os.path.exists(backup_path):
                os.makedirs(backup_path)

            full_filename = os.path.join(backup_path, filename)
            with open(full_filename, 'wb') as backup_file:
                backup_file.write(base64.b64decode(data))

            self.database_info_id = False
            return {
                'type': 'ir.actions.act_window',
                'res_model': self._name,
                'view_mode': 'form',
                'res_id': self.id,
                'target': 'new',
            }

        except Exception as e:
            _logger.error(e)
            raise UserError(e)
        return True

    @api.multi
    def button_drop_database(self):
        try:
            dbname = self.database_info_id.name
            odoo.service.db.exp_drop(dbname)
            self.sudo().database_info_id.unlink()

            if self.delete_backup_files:
                backup_path = os.path.join(self.env.user.sudo().personal_data_path or '', 'backups', dbname)
                if os.path.exists(backup_path):
                    shutil.rmtree(backup_path)

            self.database_info_id = False
            return {
                'type': 'ir.actions.act_window',
                'res_model': self._name,
                'view_mode': 'form',
                'res_id': self.id,
                'target': 'new',
            }
        except Exception as e:
            raise UserError(e)
        return True

    # def _get_sftp_connection(self,
    #                          sftp_host, sftp_port,
    #                          sftp_user, sftp_password, sftp_private_key=False):
    #     """Return a new SFTP connection with supplied parameters."""
    #     params = {
    #         "host": sftp_host,
    #         "username": sftp_user,
    #         "port": sftp_port,
    #     }
    #     _logger.debug(
    #         "Trying to connect to sftp://%(username)s@%(host)s:%(port)d",
    #         extra=params)
    #     if sftp_private_key:
    #         params["private_key"] = sftp_private_key
    #         if sftp_password:
    #             params["private_key_pass"] = sftp_password
    #     else:
    #         params["password"] = sftp_password
    #     return pysftp.Connection(**params)

    def restore_db(self, db, dump_file, copy=False):
        assert isinstance(db, pycompat.string_types)
        if odoo.service.db.exp_db_exist(db):
            _logger.info('RESTORE DB: %s already exists', db)
            raise Exception("Database already exists")

        odoo.service.db._create_empty_database(db)

        filestore_path = None
        with odoo.tools.osutil.tempdir() as dump_dir:
            if zipfile.is_zipfile(dump_file):
                # v8 format
                with zipfile.ZipFile(dump_file, 'r') as z:
                    # only extract known members!
                    filestore = [m for m in z.namelist() if m.startswith('filestore/')]
                    z.extractall(dump_dir, ['dump.sql'] + filestore)

                    if filestore:
                        filestore_path = os.path.join(dump_dir, 'filestore')

                pg_cmd = 'psql'
                pg_args = ['-q', '-f', os.path.join(dump_dir, 'dump.sql')]

            else:
                # <= 7.0 format (raw pg_dump output)
                pg_cmd = 'pg_restore'
                pg_args = ['--no-owner', dump_file]

            args = []
            args.append('--dbname=' + db)
            pg_args = args + pg_args

            if odoo.tools.exec_pg_command(pg_cmd, *pg_args):
                raise Exception("Couldn't restore database")

            registry = odoo.modules.registry.Registry.new(db)
            with registry.cursor() as cr:
                env = odoo.api.Environment(cr, SUPERUSER_ID, {})
                if copy:
                    # if it's a copy of a database, force generation of a new dbuuid
                    env['ir.config_parameter'].init(force=True)
                if filestore_path:
                    # filestore_dest = env['ir.attachment']._filestore()
                    filestore_dest = os.path.join(self.env.user.sudo().personal_data_path, 'filestore', db)
                    # filestore_dest = env['ir.attachment']._filestore()
                    shutil.move(filestore_path, filestore_dest)

                if odoo.tools.config['unaccent']:
                    try:
                        with cr.savepoint():
                            cr.execute("CREATE EXTENSION unaccent")
                    except psycopg2.Error:
                        pass

        _logger.info('RESTORE DB: %s', db)

    @api.multi
    def button_restore_database(self):
        # _logger.info('####button_restore_database####')
        try:
            # self._check_db_name(self.backup_db_name)
            filepath = ''
            # if self.recovery_type == 'personal_path':
            #     filepath = self.perso_db_backup_file
            # elif self.recovery_type == 'production_server':
                # backup_path = self.env['ct_project.config.settings'].get_value('db_backup_dir')
                # filepath = os.path.join(backup_path, self.db_backup_file)
                # _logger.warning('#################################%s###########################', filepath)
            filepath = self.db_backup_file.fullname
                # with open(filepath, 'rb') as backup_file:
                #     _logger.warning('#####################OPENED##########################')
                #     data = base64.b64encode(backup_file.read())
                #     db_name = '%s.%s' % (self.backup_db_name, self.env.user.sudo().docker_db_suffix)
                #     odoo.service.db.exp_restore(db_name, data, True)
                #     return True

            _logger.warning('Trying to restore %s', filepath)
            db_name = '%s.%s' % (self.backup_db_name, self.env.user.sudo().docker_db_suffix)
            self._check_db_name(db_name)
            self.restore_db(db_name, filepath, copy=True)

            info = self.env['c1_project_dev.userdb.info'].create({
                'name': db_name,
                'login': self.login_restore,
                'passwd': self.passwd_restore,
                'user_id': self.env.uid,
                'user_ids': [(6, 0, [self.env.uid])],
            })
        except Exception as e:
            raise UserError(e)
        return True

    @api.multi
    def button_duplicate_database(self):
        try:
            self._check_db_name(self.db_copy_name or '')
            db_copy_name = '%s.%s' % (self.db_copy_name, self.env.user.sudo().docker_db_suffix)
            # odoo.service.db.exp_duplicate_database(self.database_info_id.name, db_copy_name)

            '''USING THE ODOO DATABASE DUPLICATION CODE IN THIS WAY TO BE ABLE TO MODIFY IT SUCH THAT IT CAN COPY THE DATA RELATED
            TO THE DATABASE IN THE DATA PATH OF THE USER'S CONTAINER'''

            _logger.info('Duplicate database `%s` to `%s`.', self.database_info_id.name, db_copy_name)
            odoo.sql_db.close_db(self.database_info_id.name)
            db = odoo.sql_db.db_connect('postgres')
            with closing(db.cursor()) as cr:
                cr.autocommit(True)  # avoid transaction block
                odoo.service.db._drop_conn(cr, self.database_info_id.name)
                cr.execute("""CREATE DATABASE "%s" ENCODING 'unicode' TEMPLATE "%s" """ % (db_copy_name, self.database_info_id.name))

            registry = odoo.modules.registry.Registry.new(db_copy_name)
            with registry.cursor() as cr:
                # if it's a copy of a database, force generation of a new dbuuid
                env = odoo.api.Environment(cr, SUPERUSER_ID, {})
                env['ir.config_parameter'].init(force=True)

            # if self.env.user.sudo().docker_instance_id:
            #     self.env.user.sudo().docker_instance_id.action_stop()

            from_fs = odoo.tools.config.filestore(self.database_info_id.name)
            _logger.warning(from_fs)
            to_fs = os.path.join(self.env.user.sudo().personal_data_path, 'filestore', db_copy_name)
            if os.path.exists(from_fs) and not os.path.exists(to_fs):
                shutil.copytree(from_fs, to_fs)

            # if self.env.user.sudo().docker_instance_id:
            #     self.env.user.sudo().docker_instance_id.action_start()

            info = self.env['c1_project_dev.userdb.info'].create({
                'name': db_copy_name,
                'login': self.database_info_id.login,
                'passwd': self.database_info_id.passwd,
                'user_id': self.env.uid,
                'user_ids': [self.env.uid],
            })

        except Exception as e:
            raise UserError(_(e.message))
        return True
