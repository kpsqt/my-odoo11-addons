# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools, SUPERUSER_ID, _


class ProjectConfiguration(models.TransientModel):
    # _name = 'ct_project.config.settings'
    _inherit = 'res.config.settings'

    @api.multi
    def action_view_log_file(self):
        return {
            'type':'ir.actions.act_window',
            'name':'Config file viewer',
            'res_model':'c1_project_dev.config_file_log_viewer.wizard',
            'view_mode':'form',
            'context':{'default_name':self.config_file_path},
            'target':'inline'
        }
    
    # @api.multi
    # def _default_get_script_path(self):
    #     if self.env['ir.values'].sudo().get_default('res.config.settings', 'ct_project_svn_script_path'):
    #         return self.env['ir.values'].sudo().get_default('res.config.settings', 'ct_project_svn_script_path')
    #     return 'odoo_getaddon_script.sh'
    #
    # @api.multi
    # def _default_get_addons_directory(self):
    #     if self.env['ir.values'].sudo().get_default('res.config.settings', 'ct_project_addons_directory'):
    #         return self.env['ir.values'].sudo().get_default('res.config.settings', 'ct_project_addons_directory')
    #     return '/data/saas/co-addons'
    #
    # @api.multi
    # def _default_get_config_file_path(self):
    #     if self.env['ir.values'].sudo().get_default('res.config.settings', 'ct_project_config_file_path'):
    #         return self.env['ir.values'].sudo().get_default('res.config.settings', 'ct_project_config_file_path')
    #     return '/data/saas/log'
    #
    # @api.multi
    # def _default_get_upload_stage(self):
    #     if self.env['ir.values'].sudo().get_default('res.config.settings', 'ct_project_upload_stage'):
    #         value = self.env['ir.values'].sudo().get_default('res.config.settings', 'ct_project_upload_stage')
    #         if value:
    #             return value
    #     return self.env.ref('c1_project_dev.test').id
    #
    # @api.multi
    # def _default_get_issue_upload_stage(self):
    #     if self.env['ir.values'].sudo().get_default('res.config.settings', 'ct_project_issue_upload_stage'):
    #         return self.env['ir.values'].sudo().get_default('res.config.settings', 'ct_project_issue_upload_stage')
    #     return self.env.ref('c1_project_dev.issue_verifying_stage').id
    #
    # @api.multi
    # def _default_get_auto_install(self):
    #     return self.env['ir.values'].sudo().get_default('res.config.settings', 'ct_project_auto_install')
    #
    # @api.multi
    # def _default_get_addons_path(self):
    #     return self.env['ir.values'].sudo().get_default('res.config.settings', 'ct_project_addons_path')
    #
    # @api.multi
    # def _default_get_docker_instance(self):
    #     return self.env['ir.values'].sudo().get_default('res.config.settings', 'ct_project_docker_instance')
    #
    @api.multi
    def _default_get_db_backup_dir(self):
        return self.env['ir.config_parameter'].sudo().get_param('ct_project_backup_files_dir')

    @api.multi
    def _default_get_svnmod_script_path(self):
        return self.env['ir.config_parameter'].sudo().get_param('ct_project_svnmod_script_path')

    @api.multi
    def _default_get_svncreate_script_path(self):
        return self.env['ir.config_parameter'].sudo().get_param('ct_project_svncreate_script_path')
    #
    # @api.multi
    # def _default_get_docker_user(self):
    #     return self.env['ir.values'].sudo().get_default('res.config.settings', 'c1_project_dev_docker_user')
    #
    # @api.multi
    # def _default_get_docker_user_passwd(self):
    #     return self.env['ir.values'].sudo().get_default('res.config.settings', 'c1_project_dev_docker_user_passwd')
    #
    # @api.multi
    # def _default_get_svn_repo_root_path(self):
    #     return self.env['ir.values'].sudo().get_default('res.config.settings',
    #                                                     'c1_project_dev_svn_repo_root_path')

    # script_path = fields.Char(string='SVN Script path', default=lambda self: self._default_get_script_path())
    # addons_directory = fields.Char(string='Addons directory', default=lambda self: self._default_get_addons_directory())
    # config_file_path = fields.Char(string='Local instance config file path', default=lambda self: self._default_get_config_file_path())
    # upload_stage = fields.Many2one('project.task.type', string='Task transfer stage',
    #                                help='Stage where the project(module) is to be transfered',
    #                                default=lambda self: self._default_get_upload_stage())
    # issue_upload_stage = fields.Many2one('project.issue.stage', string='Issue transfer stage',
    #                                help='Stage where the project(module) linked to the issue is to be transfered',
    #                                default=lambda self: self._default_get_issue_upload_stage())
    # auto_install = fields.Boolean(string='Auto-Install', default=lambda self: self._default_get_auto_install(), help='Install automatically the module after the transfer')
    # addons_path = fields.Char(string='Addons path', default=lambda self: self._default_get_addons_path(), help='Addons path used for installation')
    # docker_instance = fields.Char(string='Docker container ID', default=lambda self: self._default_get_docker_instance(), help='Name of the docker instance used to run odoo')
    # docker_user = fields.Char(string='Docker user', default=lambda self: self._default_get_docker_user(), help='username of sudo-er user in the docker instance')
    # docker_user_passwd = fields.Char(string='Docker user\'s password', default=lambda self: self._default_get_docker_user_passwd(), help='username of sudo-er user in the docker instance')
    db_backup_dir = fields.Char(string='Database backup files directory', default=lambda self: self._default_get_db_backup_dir(), help='Directory where backup files are stored')
    # svn_repo_root_path = fields.Char(string='Svn repository root path', default=lambda self: self._default_get_svn_repo_root_path(), help='')
    svncreate_script_path = fields.Char(string='Svn module creation script path', default=lambda self: self._default_get_svncreate_script_path())
    svnmod_script_path = fields.Char(string='Svn access right modification script', default=lambda self: self._default_get_svnmod_script_path())

    # @api.multi
    # def set_script_path_defaults(self):
    #     return self.env['ir.values'].sudo().set_default(
    #         'res.config.settings', 'ct_project_svn_script_path', self.script_path)
    #
    # @api.multi
    # def set_addons_directory_defaults(self):
    #     return self.env['ir.values'].sudo().set_default(
    #         'res.config.settings', 'ct_project_addons_directory', self.addons_directory)
    #
    # @api.multi
    # def set_config_file_path_defaults(self):
    #     return self.env['ir.values'].sudo().set_default(
    #         'res.config.settings', 'ct_project_config_file_path', self.config_file_path)
    #
    # @api.multi
    # def set_upload_stage_defaults(self):
    #     return self.env['ir.values'].sudo().set_default(
    #         'res.config.settings', 'ct_project_upload_stage', self.upload_stage.id)
    #
    # @api.multi
    # def set_issue_upload_stage_defaults(self):
    #     return self.env['ir.values'].sudo().set_default(
    #         'res.config.settings', 'ct_project_issue_upload_stage', self.issue_upload_stage.id)
    #
    # @api.multi
    # def set_auto_install_defaults(self):
    #     return self.env['ir.values'].sudo().set_default(
    #         'res.config.settings', 'ct_project_auto_install', self.auto_install)
    #
    # @api.multi
    # def set_addons_path_defaults(self):
    #     return self.env['ir.values'].sudo().set_default(
    #         'res.config.settings', 'ct_project_addons_path', self.addons_path)
    #
    # @api.multi
    # def set_docker_instance(self):
    #     return self.env['ir.values'].sudo().set_default(
    #         'res.config.settings', 'ct_project_docker_instance', self.docker_instance)
    #
    # @api.multi
    # def set_docker_user(self):
    #     return self.env['ir.values'].sudo().set_default(
    #         'res.config.settings', 'c1_project_dev_docker_user', self.docker_user)
    #
    # @api.multi
    # def set_docker_user_passwd(self):
    #     return self.env['ir.values'].sudo().set_default(
    #         'res.config.settings', 'c1_project_dev_docker_user_passwd', self.docker_user_passwd)
    #
    # @api.multi
    # def set_db_backup_dir(self):
    #     return self.env['ir.config_parameter'].sudo().set_param('ct_project_backup_files_dir', self.db_backup_dir)
    #
    # @api.multi
    # def set_svn_repo_root_path(self):
    #     return self.env['ir.values'].sudo().set_default(
    #         'res.config.settings', 'c1_project_dev_svn_repo_root_path', self.svn_repo_root_path)
    #
    # def get_value(self, param):
    #     return self.env['ir.values'].sudo().get_default('res.config.settings', param)

    def get_values(self):
        res = super(ProjectConfiguration, self).get_values()
        res.update(
            db_backup_dir=self.env['ir.config_parameter'].sudo().get_param('c1_project_dev.db_backup_dir'),
            svnmod_script_path=self.env['ir.config_parameter'].sudo().get_param('ct_project_svnmod_script_path'),
            svncreate_script_path=self.env['ir.config_parameter'].sudo().get_param('ct_project_svncreate_script_path')
        )
        return res

    def set_values(self):
        super(ProjectConfiguration, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('c1_project_dev.db_backup_dir', self.db_backup_dir)
        self.env['ir.config_parameter'].sudo().set_param('c1_project_dev.svnmod_script_path', self.svnmod_script_path)
        self.env['ir.config_parameter'].sudo().set_param('c1_project_dev.svncreate_script_path', self.svncreate_script_path)

