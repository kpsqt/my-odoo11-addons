# -*- coding: utf-8 -*-
import datetime
import docker
from lxml import etree

from odoo import api, fields, models, tools, SUPERUSER_ID, _
from odoo.exceptions import UserError, ValidationError, AccessError
from odoo.tools.safe_eval import safe_eval
from odoo.tools import pycompat
import subprocess
import os
import pip
import ast
import json
import re
import logging

_logger = logging.getLogger(__name__)

import svn
from svn.exception import SvnException
import svn.common
import svn.remote
import svn.local
import git

from ..utils import svn_utils

PROJECT_TYPES_SELECTION = [
        ('qitongyun', 'Qitong Cloud'),
        ('yongyou', 'YonYou'),
    ]

def get_setting_value(self, param):
    # return self.env['ir.values'].sudo().get_default(
    #     'res.config.settings', param)
    return self.env['res.config.settings'].sudo().get_values().get(param)


class TaskStage(models.Model):
    _inherit = 'project.task.type'

    # @api.multi
    # def name_get(self):
    #     res = []
    #
    #     return res

    is_initial = fields.Boolean(string='Initial stage', help='If a task can be initiated at this stage')
    doublon_allowed = fields.Boolean(string='Doubles allowed',
                                     help='If this stage can contain many tasks having the same technical name',
                                     translated=True, default=True)
    parent_stage = fields.Many2one('project.task.type', string='Precedent stage', translated=True)
    user_ids = fields.Many2many('res.users', string='Responsible users', translated=True)
    related_fields = fields.Many2many('ir.model.fields', string='Related fields', translated=True,
                                      domain=[('model_id.model', '=', 'project.task')])


class StageAdministrationRules(models.Model):
    _name = 'c1_project_dev.stage_administration_rules'

    @api.onchange('stage_id')
    def onchange_stage_id(self):
        # print 'onchange---stage_id'
        return {
            'domain': {
                'users': [('id', 'in', [self.stage_id.mapped('user_ids.id')])]
            }
        }

    users = fields.Many2many('res.users', string='Responsible users')
    task_id = fields.Many2one('project.task', string='Task')
    stage_id = fields.Many2one('project.task.type', string='Stage')


class Task(models.Model):
    _inherit = 'project.task'

    _logger = logging.getLogger(__name__)

    @api.onchange('stage_id')
    def _onchange_stage(self):
        # print 'stage changed!!!'
        return {}

    @api.depends('stage_id', 'kanban_state')
    def _compute_transferable(self):
        # print '***********compute transferable**********'
        # transfer_stage = self.env['project.task.type'].search([('id','=',get_setting_value(self, 'ct_project_upload_stage'))], limit=1)
        # for rec in self:
        #     if transfer_stage:
        #         rec.transferable = rec.stage_id and (rec.stage_id.id != transfer_stage.id and rec.stage_id.sequence <= transfer_stage.sequence) or False
        for rec in self:
            rec.transferable = (rec.stage_id == self.env.ref('c1_project_dev.development',
                                                             raise_if_not_found=False)) and (rec.kanban_state == 'done')

    @api.depends('stage_id')
    def _compute_reversible(self):
        # print '***********compute reversible**********'
        transfer_stage = self.env['project.task.type'].search(
            [('id', '=', get_setting_value(self, 'ct_project_upload_stage'))], limit=1)
        for rec in self:
            if transfer_stage:
                # print 'Transfer stage sq : ', transfer_stage.sequence
                # print 'record stage sq: ', rec.stage_id.sequence
                rec.reversible = rec.stage_id and (
                    rec.stage_id.sequence >= transfer_stage.sequence and rec.stage_id.sequence <= transfer_stage.sequence) or False

    @api.depends('transfer_ids')
    def _compute_last_transfer_revision(self):
        for rec in self:
            revs = rec.transfer_ids.mapped('revision')
            # print revs
            if len(revs) >= 2:
                rec.last_transfer_revision = revs[1]
            elif len(revs):
                rec.last_transfer_revision = revs[0]
            else:
                rec.last_transfer_revision = False

    @api.depends('transfer_ids')
    def _compute_current_transfer_revision(self):
        for rec in self:
            revs = rec.transfer_ids.mapped('revision')
            # print revs
            if len(revs):
                rec.current_transfer_revision = revs[0]
            else:
                rec.current_transfer_revision = False

    # def _compute_issue_count(self):
    #     Issues = self.env['project.issue']
    #     for rec in self:
    #         rec.issue_count = Issues.search_count([('task_id','=', rec.id)])

    default_description = "第一部分：应用场景" + '<br/><br/>' + "" \
                                                       "第二部分：开发设计" + '<br/><br/>' + "" \
                                                                                    "第三部分：开发描述及界面设计" + '<br/>' + "" \
                                                                                                                 "功能：" + '<br/>' + "" \
                                                                                                                                   "1.菜单" + '<br/>' + "" \
                                                                                                                                                      "2.字段说明" + '<br/><br/>' + "" \
                                                                                                                                                                                " 3.控制说明" + '<br/><br/>' + "" \
                                                                                                                                                                                                           "4.权限说明" + '<br/><br/>' + ""

    default_development_description = _(
        "<h3>Usage explanation</h3><p></p>"
        "<h3>Things to avoid doing</h3><p></p>"
        "<h3>Technical specifications</h3><p></p>"
        "<h3>Possible issues</h3><p></p>"
    )

    @api.multi
    def _compute_downloaded(self):
        for rec in self:
            if rec.module_id:
                rec.downloaded = os.path.exists(
                    os.path.join(self.env.user.sudo().personal_addons_path, rec.module_id.name)
                )

    # def _default_stage_responsibles(self):
    #     res = []
    #     res2 = []
    #     Projects = self.env['project.project']
    #     project_id = self.env.context.get('default_project_id')
    #     active_model = self.env.context.get('active_model')
    #     # print active_model
    #     if not project_id:
    #         return res
    #
    #     if active_model != 'project.project':
    #         return res
    #
    #     project = Projects.search([('id','=',project_id)], limit=1)
    #     if project:
    #         res = [ (0, 0, {'users': [(6,0,stage.user_ids.mapped('id'))], 'stage_id': stage.id }) for stage in project.type_ids ]
    #     return res


    def _compute_ready_to_deploy(self):
        for rec in self:
            rec.ready_for_deployment = rec.kanban_state == 'done' and rec.stage_id == self.env.ref(
                'c1_project_dev.deployment')

    task_user_ids = fields.Many2many('res.users', string='Team Member')
    testreq_ids = fields.One2many('test.requirement', 'task_id', string='Test Requirement')
    '''the users assigned to the task must be svn users'''
    # testcase_ids = fields.One2many('test.case', 'task_id', string='测试用例', domain=[('is_svn_user','=',True)])
    testcase_ids = fields.One2many('test.case', 'task_id', string='Test Case')
    module_id = fields.Many2one('c1_project_dev.module', string='Module', domain=[('active', '=', True)])
    installable = fields.Boolean(string='Can be installed', related='module_id.installable', readonly=True)
    technical_name = fields.Char(string='Technical name', related='module_id.technical_name', readonly=True)
    transferable = fields.Boolean(compute='_compute_transferable', store=True)
    reversible = fields.Boolean(compute='_compute_reversible', store=True)
    transfer_ids = fields.One2many('c1_project_dev.transfer', 'task_id', string='Transfer details', readonly=True)
    last_transfer_revision = fields.Integer(string='Last transfer revision', compute='_compute_last_transfer_revision',
                                            tranlated=True)
    current_transfer_revision = fields.Integer(string='Current transfer revision',
                                               compute='_compute_current_transfer_revision', tranlated=True)
    issue_count = fields.Integer(string='', compute='_compute_issue_count')
    analysis_description = fields.Html(string='Analysis Description')
    development_description = fields.Html(string='Development description', default=default_development_description,
                                          translate=True)
    # prototyping_description = fields.Html(string='Prototyping description', translate=True)
    deployment_description = fields.Html(string='Deployment description', translate=True)
    cancellation_description = fields.Html(string='Cancellation description', translate=True)
    description = fields.Html(string='Description', default=default_description)
    stage_responsibles = fields.One2many('c1_project_dev.stage_administration_rules', 'task_id',
                                         string='Stage Responsibles',
                                         # default=_default_stage_responsibles
                                         )
    # downloaded = fields.Boolean(string='Downloaded', compute='_compute_downloaded', help='If the module has already been downloaded to current user\'s personal path')
    downloaded = fields.Boolean(string='Downloaded', related='module_id.downloaded',
                                help='If the module has already been downloaded to current user\'s personal path')
    current_downloaded_rev = fields.Integer(string='Downloaded Revision', related='module_id.current_downloaded_rev',
                                            translated=True)
    ready_for_deployment = fields.Boolean(string='Ready for deployment', compute='_compute_ready_to_deploy')
    type = fields.Selection([('normal', 'Normal'), ('feedback', 'Feedback')], string='Type')

    project_type = fields.Selection(PROJECT_TYPES_SELECTION, related='project_id.project_type', readonly=True)

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        result = super(Task, self).fields_view_get(view_id, view_type, toolbar=toolbar, submenu=submenu)

        if view_type == 'form':
            doc = etree.XML(result['arch'])
            pages = doc.xpath("//page")
            for page in pages:
                # print page.attrib
                modifiers = page.attrib.get('modifiers', '{}')
                modifiers = modifiers.replace('true', 'True').replace('false', 'False')
                modifiers = ast.literal_eval(modifiers)
                # modifiers = safe_eval(modifiers)
                if modifiers.get('readonly'):
                    # print modifiers
                    fields = page.findall('field')
                    for field in fields:
                        # print field.attrib.get('name'), field.attrib.get('domain','[]')
                        field_modifiers = field.attrib.get('modifiers')
                        # print field_modifiers
                        field_modifiers = ast.literal_eval(
                            field_modifiers.replace('true', 'True').replace('false', 'False'))
                        field_readonly = field_modifiers.get('readonly', [])
                        if not isinstance(field_readonly, bool):
                            field_readonly.append(modifiers.get('readonly')[0])
                        field_modifiers.update({'readonly': field_readonly})
                        field.set('modifiers', json.dumps(field_modifiers))
                        # field.set('modifiers', repr(field_modifiers))
                        # print field_modifiers
            result['arch'] = etree.tostring(doc)
        return result

    @api.multi
    def action_mark_module_revision(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'c1_project_dev.module.review.wizard',
            'form_type': 'form',
            'view_mode': 'form',
            'context': {'default_module_id': self.module_id and self.module_id.id or False},
            'view_id': self.env.ref('c1_project_dev.wizard_mark_module_rev').id,
            'target': 'new',
        }

    @api.multi
    def action_deploy_module(self):

        # if not self.env.user.sudo().has_group('project.group_project_manager') or not self.env.user.sudo().has_group('c1_project_.group_project_manager')
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'c1_project_dev.module.deployment.wizard',
            'form_type': 'form',
            'view_mode': 'form',
            'context': {
                'default_module_id': self.module_id and self.module_id.id or False,
                'default_task_id': self.id,
                'refresh_ui': True,
            },
            'target': 'new',
        }

    @api.multi
    def action_manage_database(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'c1_project_dev.database.wizard',
            'form_type': 'form',
            'view_mode': 'form',
            # 'context': {'default_module_id': self.module_id and self.module_id.id or False},
            'view_id': self.env.ref('c1_project_dev.wizard_db_manage_view').id,
            'target': 'new',
        }

    @api.multi
    def action_check_dependencies(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'c1_project_dev.module_dependencies.wizard',
            'form_type': 'form',
            'view_mode': 'form',
            'context': {'default_module_id': self.module_id and self.module_id.id or False},
            'view_id': self.env.ref('c1_project_dev.module_dep_wizard_form_view').id,
            'target': 'new',
        }

    @api.multi
    def action_install_module(self):
        if not self.downloaded:
            _logger.error("NOT INSTALLED MODULE")
            raise UserError(_('"%s" is not in you personal addons path. '
                              'Please make sure you have downloaded it or contact your administrator if you think this is an error') % (
                                self.module_id and self.module_id.name or False,))
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'c1_project_dev.module.wizard',
            'form_type': 'form',
            'view_mode': 'form',
            'context': {
                'default_module_id': self.module_id and self.module_id.id or False,
                'default_repository_id': self.project_id.repository_id.id
            },
            'view_id': self.env.ref('c1_project_dev.wizard_module_install_view').id,
            'target': 'new',
        }

    @api.multi
    def action_run_cmd(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'c1_project_dev.linux_cmd.wizard',
            'form_type': 'form',
            'view_mode': 'form',
            'view_id': self.env.ref('c1_project_dev.cmd_wizard_form_view').id,
            'target': 'new',
        }

    @api.multi
    def action_task_issues(self):
        action = self.env.ref('project_issue.project_issue_categ_act0').read()[0]
        action['domain'] = [('task_id', '=', self.id)]
        new_context = ast.literal_eval(action['context'].replace(" ", "").replace("\n", "").replace("active_id", "''"))

        active_model = self.env.context.get('active_model')
        active_id = self.env.context.get('active_id')
        # print active_model, active_id

        if active_id and active_model == 'project.project':
            new_context.update({
                'default_project_id': active_id,
                'default_task_id': self.id,
                'active_id': active_id,
                'active_ids': [active_id],
                'active_model': active_model,
            })
        else:
            new_context.update({
                'default_project_id': self.project_id and self.project_id.id or False,
                'default_task_id': self.id,
                'active_id': self.project_id and self.project_id.id or False,
                'active_ids': [self.project_id and self.project_id.id or False],
                'active_model': 'project.project',
            })

        action['context'] = new_context
        return action

    @api.multi
    def action_install_dependencies(self):
        if not self.module_id:
            return False

        return self.module_id.install_dependencies()

    @api.multi
    def action_transfer_module(self):
        # if not (self.env.uid in self.task_user_ids.mapped('id') and self.env.uid in self.project_id.svn_user_ids.mapped('id')):
        # if self.env.uid not in self.project_id.svn_user_ids.mapped('id'):
        #     # raise UserError(_('Only SVN users assigned to the project "%s" and this task can update it to this stage.') %  self.project_id.name)
        #     raise AccessError(
        #         _('Only SVN users assigned as tester to the project "%s" can use this.') % self.project_id.name)

        # if self.kanban_state != 'done':
        #     raise UserError(_('Action forbidden till this task is marked as "done"'))

        # if not self.installable:
        #     raise UserError(_('This task cannot be uploaded because the dependence requirements of the related module are not met.'))

        res = {
            'name': 'Module Download Wizard',
            'type': 'ir.actions.act_window',
            # 'res_model': 'c1_project_dev.svn_checkout_wizard',
            'res_model': 'c1_project_dev.module.copy.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_module_id': self.module_id and self.module_id.id or False,
            },
        }
        if self.env.context.get('active_model') == 'project.project':
            res['context'].update({'active_project': self.env.context.get('active_id')})
        return res

    @api.multi
    def action_revert_module(self):
        # if not (self.env.uid in self.task_user_ids.mapped('id') and self.env.uid in self.project_id.svn_user_ids.mapped('id')):
        if self.env.uid not in self.project_id.svn_user_ids.mapped('id'):
            # raise UserError(_('Only SVN users assigned to the project "%s" and this task can update it to this stage.') %  self.project_id.name)
            raise AccessError(
                _('Only SVN users assigned to the project "%s" can update it to this stage.') % self.project_id.name)

        res = {
            'name': 'Module Transfer Revert Wizard',
            'type': 'ir.actions.act_window',
            'res_model': 'c1_project_dev.svn_wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_task_id': self.id,
                'default_name': self.technical_name,
                'default_sender_svn_account': self.env.user.svn_account,
                'default_sender_svn_password': self.env.user.svn_password,
                'default_svn_repository': self.project_id.repository_url,
                'default_state': 'revert',
                'default_version': bool(self.last_transfer_revision) and str(self.last_transfer_revision) or False,
                'current_stage': self.stage_id and self.stage_id.id or False
            },
        }
        if self.env.context.get('active_model') == 'project.project':
            res['context'].update({'active_project': self.env.context.get('active_id')})
        return res

    @api.multi
    def action_assign_to_project(self):
        res = {
            'name': 'Assign to project',
            'type': 'ir.actions.act_window',
            'res_model': 'c1_project_dev.feedback.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_task_id': self.id,
            },
        }
        return res

    @api.constrains('stage_id')
    def _check_stage(self):
        ProjectTask = self.env['project.task']
        ProjectTaskType = self.env['project.task.type']
        sensitive_stage_ids = ProjectTaskType.search([('doublon_allowed', '=', False)]).mapped('id')
        for record in self:
            if record.stage_id and record.stage_id.id in sensitive_stage_ids:
                search_domain = [('technical_name', '=', record.technical_name), ('stage_id', '=', record.stage_id.id)]
                count = ProjectTask.search_count(search_domain)
                if count > 1:
                    raise ValidationError(
                        _(
                            "Impossible to have many tasks with the same technical name in the stage '%s'" % record.stage_id.name))

    @api.multi
    def onchange_project_id(self):
        for record in self:
            if record.project_id:
                record.stage_responsibles.unlink()
                for stage in record.mapped('project_id.type_ids'):
                    # _logger.info(stage)
                    record.stage_responsibles.sudo().create({
                        'users': [(6, 0, stage.user_ids.mapped('id'))],
                        'stage_id': stage.id,
                        'task_id': record.id,
                    })

    # ------------------------------------------------
    # CRUD overrides
    # ------------------------------------------------

    @api.model
    def create(self, vals):
        #         if self.env.uid not in self.env.ref('project.group_project_manager').users.mapped('id'):
        #             raise UserError(_('Only Project managers can create tasks.'))
        # print vals
        if vals.get('stage_id'):
            search_domain = [('id', '=', vals['stage_id']), ('is_initial', '=', True)]
            stage = self.env['project.task.type'].search(search_domain, limit=1)
            if not stage:
                raise UserError(_('A task cannot be created at this stage.'))
        new_record = super(Task, self).create(vals)

        for stage in new_record.mapped('project_id.type_ids'):
            # _logger.info(stage)
            new_record.stage_responsibles.sudo().create({
                'users': [(6, 0, stage.user_ids.mapped('id'))],
                'stage_id': stage.id,
                'task_id': new_record.id,
            })

        # print new_record.stage_id
        for r in new_record.stage_responsibles:
            if r.stage_id.id == new_record.stage_id.id:
                # print r.stage_id, r.users.mapped('partner_id')
                new_followers = r.users.mapped('partner_id') - new_record.message_partner_ids
                new_record.message_subscribe(new_followers.ids)
                break
        return new_record

    @api.multi
    def write(self, vals):
        # _logger.debug(self.env.context)
        TaskStage = self.env['project.task.type']
        Wizard = self.env['c1_project_dev.svn_wizard']
        '''
        Checking if the fields to be modified are related to some stages
        and if the user has the right to modify the fields related to the current stage:
        foreach stage:
            check if one of the fields to be modified related to the stage
            if related to the stage, check if the user is one of the allowed users to manage the stage.'''

        '''Check first for the current stage'''
        current_stage_related_fields = set([])
        if self.stage_id:
            current_stage_related_fields = set(self.stage_id.mapped('related_fields.name'))
            stage_info = self.stage_responsibles.filtered(lambda record: record.stage_id == self.stage_id)
            # stage_related_users = stage_info and set(stage_info.mapped('users.id')) or set(self.stage_id.mapped('user_ids.id'))
            stage_related_users = stage_info and set(stage_info.mapped('users.id')) or set([])
            print(stage_related_users)
            if bool(len(current_stage_related_fields.intersection(set(vals.keys())))) and (
                        self.env.uid not in stage_related_users):
                raise AccessError(_(
                    'The current user is not authorized to perform this action. Make sure the user has access rights on the fields related to the stage "%s"') % self.stage_id.name)

        '''Then check for the remaining stages'''
        for stage in self.project_id.type_ids.filtered(lambda record: record != self.stage_id):
            stage_related_fields = set(stage.mapped('related_fields.name'))
            # _logger.warning('###########################################################################')
            # remove fields that are allowed for the current stage but related to other stages as well
            # produces as effect that: the sur can access this field on this current state but wouldnt be able to for other stages
            for f in current_stage_related_fields:
                try:
                    stage_related_fields.remove(f)
                except Exception as p:
                    _logger.exception(p)
                    continue

            stage_info = self.stage_responsibles.filtered(lambda record: record.stage_id == stage)
            # stage_related_users = stage_info and set(stage_info.mapped('users.id')) or set(stage.mapped('user_ids.id'))
            stage_related_users = stage_info and set(stage_info.mapped('users.id')) or set([])
            if bool(len(stage_related_fields.intersection(set(vals.keys())))) and (
                        self.env.uid not in stage_related_users):
                raise AccessError(_(
                    'The current user is not authorized to perform this action. Make sure the user has access rights on the fields related to the stage "%s"') % stage.name)

        # # stage_related_fields = set(self.project_id.type_ids.mapped('related_fields.name'))
        # stage_related_fields = set(self.stage_id.mapped('related_fields.name'))
        # # stage_related_users = set(self.project_id.type_ids.mapped('user_ids.id'))
        # stage_related_users = set(self.stage_id.mapped('user_ids.id'))
        # if bool( len(stage_related_fields.intersection( set(vals.keys()) )) ) and (self.env.uid not in stage_related_users):
        #     raise AccessError(_(
        #         'The current user is not authorized to perform this action. Make sure the user has access rights on the fields related to the stage "%s"') % self.stage_id.name)

        # previous_stage_responsibles = []
        if 'stage_id' in vals:
            previous_stage = self.stage_id
            new_stage = TaskStage.search([('id', '=', vals['stage_id'])], limit=1)
            if (previous_stage and new_stage) and (
                        previous_stage.sequence < new_stage.sequence) and self.kanban_state != 'done':
                raise UserError(_('Cannot change the stage of a task till it is marked as "done"'))

            if new_stage == self.env.ref('c1_project_dev.done') and not self.env.context.get('action_deploy'):
                raise UserError(_('The task cannot be updated to the stage "%s" in this way') % (new_stage.name))

            previous_stage_responsibles = self.stage_responsibles.filtered(
                lambda r: r.stage_id == previous_stage).mapped('users.partner_id')
            new_stage_responsibles = self.stage_responsibles.filtered(lambda r: r.stage_id == new_stage).mapped(
                'users.partner_id')
            # # subscribe new users
            # The stage is about to change, so we add the responsibles of the new stage to the followers list
            # such that the responsibles of the current stage and the responsibles of the new stage will receive the message

            new_followers = new_stage_responsibles - self.message_partner_ids
            self.message_subscribe(new_followers.ids)

        if 'stage_id' in vals and self.env.context.get('from_ui', False):

            vals.update({'kanban_state': 'normal'})
        result = super(Task, self).write(vals)

        if vals.get('kanban_state', '') in ['done', 'blocked']:
            body = ''
            if vals['kanban_state'] == 'done':
                body = _('The task \'%s\' is ready for next stage') % self.name
            elif vals['kanban_state'] == 'blocked':
                subtype = 'project.mt_task_ready'
                body = _('The task \'%s\' is blocked') % self.name
            self.message_post(body=body, partner_ids=self.message_partner_ids.mapped('id'), context=self.env.context)

        # After the stage has been updated and the new stage responsibles and the previous stage responsibles
        # have received the notification message, we unsubscribe the responsibles of the previous stage

        if 'stage_id' in vals:
            self.message_post(body=_("The task '%s' is now under your responsibility at the stage '%s'")
                                   % (self.name, self.stage_id.name), partner_ids=new_stage_responsibles.mapped('id'),
                              context=self.env.context)

            self.message_unsubscribe(
                previous_stage_responsibles.filtered(lambda r,: r.id not in new_stage_responsibles.mapped('id')).ids
            )

            developers = self.stage_responsibles.filtered(
                lambda r: r.stage_id == self.env.ref('c1_project_dev.development')).mapped('users')
            if new_stage == self.env.ref('c1_project_dev.development'):
                if len(developers) == 0:
                    raise UserError(_(
                        'No developers assigned'
                    ))

            if new_stage.sequence > self.env.ref('c1_project_dev.development').sequence:
                try:
                    # remove user's rights when the task leaves the development stage
                    ''' sed -i "/kps@cotong.com/d" /data/repo/ctcloud/c1_project_dev/conf/authz'''
                    if self.module_id.repository_id.repository_type == 'svn':
                        for developer in developers:
                            # for developer in developers:
                            #     script = '''/%s/d''' % (developer.sudo().svn_account or False)f
                            #     # _logger.info(script)
                            #     args = ['sed', '--in-place', script,
                            #         # os.path.join(self.project_id.mapped('repository_id.physical_path')[0] or '', '%s/conf/authz' % self.technical_name)
                            #             self.module_id.authz_file
                            #         ]
                            #     cmd = '%s %s %s %s' % (args[0], args[1], args[2], args[3])
                            #     _logger.info(cmd)
                            #     output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, stdin=subprocess.PIPE, shell=True)
                            #     # _logger.info(output)

                            # if not developer.sudo().svn_account:
                            #     raise UserError(_('User information'))

                            # if developer.sudo().svn_account_id.repository_id != self.module_id.repository_id:
                            #     raise UserError(_('Make sure %s has an account registered in %s repository') % (developer.sudo().name, developer.sudo()))

                            svn_utils.grant_acces_right(
                                os.path.join(self.module_id.repository_id.physical_path, self.module_id.technical_name),
                                developer.sudo().svn_account,
                                'd')
                except subprocess.CalledProcessError as e:
                    _logger.exception(e)
                    _logger.error(e.message)
            else:
                try:
                    ''' grep -q -e 'kps@cotong = rw' ./ct_routine_task/conf/authz && sed -i "/[/]/a\kps@cotong.com = rw" /data/repo/ctcloud/ct_routine_task/conf/authz
                        sed -i "/\[\/\]/a\kps@cotong.com = rw" /data/repo/ctcloud/c1_project_dev/conf/authz
                    '''
                    # give developer read write rights
                    # for developer in developers:
                    #     args = ['sed', '--in-place', '''"/[/]/a\%s = rw"''' %
                    #             (developer.sudo().svn_account or False),
                    #             # os.path.join(self.project_id.mapped('repository_id.physical_path')[0] or '', '%s/conf/authz' % self.technical_name)
                    #             self.module_id.authz_file
                    #     ]
                    #
                    #     cmd = "%s %s /%s/d %s && %s %s %s %s" % (
                    #         args[0], args[1],
                    #         developer.sudo().svn_account or False,
                    #         args[3], args[0], args[1], args[2], args[3])
                    #
                    #     _logger.info(cmd)
                    #     output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, stdin=subprocess.PIPE,
                    #                                      shell=True)
                    for developer in developers:
                        svn_utils.grant_acces_right(
                            os.path.join(self.module_id.repository_id.physical_path or '',
                                         self.module_id.technical_name),
                            developer.sudo().svn_account,
                            'rw')

                except subprocess.CalledProcessError as e2:
                    _logger.error(e2.output)
                    _logger.error(e2.message)
                except Exception as e:
                    _logger.exception(e)
                    raise UserError(e)

        return result

    def unlink(self):
        if self.env.uid not in self.env.ref('project.group_project_manager').users.mapped('id'):
            raise UserError(_('Only Project managers can delete tasks.'))
        return super(Task, self).unlink()


class TestRequirement(models.Model):
    _name = 'test.requirement'
    _description = 'Test Requirement'
    _order = 'sequence, id'

    task_id = fields.Many2one('project.task', string='Task', index=True)
    sequence = fields.Char(string='Req No.', required=True, index=True)
    description = fields.Char(string='Req Description', translate=True, required=True)
    exe_step = fields.Char(string='Execute Step', translate=True, required=True)
    expect_result = fields.Char(string='Expect Result', translate=True, required=True)
    dev_user_id = fields.Many2one('res.users', string='Developer', default=lambda self: self.env.uid)
    dev_finish_date = fields.Datetime(string='Finish Time', default=fields.Datetime.now)


class TestCase(models.Model):
    _name = 'test.case'
    _description = 'Test Case'
    _order = 'sequence, id'

    task_id = fields.Many2one('project.task', string='Task', index=True)
    sequence = fields.Char(string='Req or Bug No.', required=True, index=True)
    test_step = fields.Char(string='Test Step', translate=True, required=True)
    test_input = fields.Char(string='Test Input', translate=True, required=True)
    expect_result = fields.Char(string='Expect Result', translate=True, required=True)
    result = fields.Selection([('normal', 'Normal'), ('blocked', 'Blocked'), ('processing', 'Processing')],
                              default='normal',
                              string='Result', translate=True, required=True, index=True)
    test_user_id = fields.Many2one('res.users', string='Tester', default=lambda self: self.env.uid)
    test_finish_date = fields.Datetime(string='Finish Time', default=fields.Datetime.now)
    note = fields.Char(string='Note', translate=True)


class Project(models.Model):
    _inherit = 'project.project'

    # @api.model
    # def _get_issue_type_common(self):
    #     IssueStage = self.env['project.issue.stage']
    #     return IssueStage.search([('case_default', '=', 1)], limit=1)

    # svn_path = fields.Char(string='SVN path', translate=True)
    # svn_user_ids = fields.Many2many(
    #     'res.users',
    #     'project_svnuser_rel',
    #     string='Testers',
    #     domain=[('is_svn_user', '=', True)])
    repository_id = fields.Many2one('c1_project_dev.repository', string='Repository')
    repository_url = fields.Char(string='SVN repository url', related='repository_id.url', readonly=True)
    project_type = fields.Selection(PROJECT_TYPES_SELECTION, string='Project type')


class Command(models.Model):
    _name = 'c1_project_dev.command'

    def _check_access_rights(self):
        # print 'checking access_rights'
        if len(self.groups):
            for group in self.groups:
                # print group.sudo().mapped('users.id')
                # print self.env.uid
                if self.env.uid in group.sudo().mapped('users.id'):
                    return True
        else:
            # if no group specified, every user can run the command
            return True
        raise AccessError(_('The current user doesnt have the right to run this command ("%s"). '
                            'Contact your administrator if you think this is an error.') % self.name)

    def run(self, cmd_args, no_exception=False):
        _logger.info('****RUNNING %s', cmd_args)
        self._check_access_rights()
        if not self.command:
            return False

        if self.params_mandatory:
            command = '%s %s' % (self.command, cmd_args)
        else:
            command = self.command

        args = command.strip().split(' ')
        try:
            output = subprocess.check_output(args, stderr=subprocess.STDOUT, stdin=subprocess.PIPE)
            return output
        except subprocess.CalledProcessError as e:
            output = e.output
            if no_exception:
                return output
            else:
                raise UserError(output)

    @api.multi
    def _compute_command(self):
        Config = self.env['res.config.settings']
        for rec in self:
            if rec.default_parameter:
                full_command = rec.cmd
                sys_params = rec.default_parameter.strip().split(',')
                for param in sys_params:
                    val = Config.get_value(param)
                    if val:
                        full_command = '%s %s' % (full_command, val)
                if rec.suffix_cmd:
                    full_command = '%s %s' % (full_command, rec.suffix_cmd.command)

                # print rec.as_sudoer
                # if rec.as_sudoer:
                #     full_command = 'echo %s | sudo %s' % (
                #     Config.get_value('c1_project_dev_docker_user_passwd'), full_command)

                rec.command = full_command
            else:
                full_command = rec.cmd
                # print rec.as_sudoer
                # if rec.as_sudoer:
                #     full_command = 'echo %s | sudo %s' % (
                #     Config.get_value('c1_project_dev_docker_user_passwd'), full_command)
                rec.command = full_command

            if rec.in_docker:
                rec.command = 'docker exec -u root -it %s %s' % (
                    self.env.user.sudo().docker_instance_id and self.env.user.sudo().docker_instance_id.name,
                    rec.command
                )

    FORBIDDEN_CMD_INPUTS = ['rm', '|']

    @api.constrains('cmd')
    def _check_cmd(self):
        for r in self:
            match = re.search(r'rm|\||&', r.cmd or '', re.M | re.I)
            if match:
                raise ValidationError(_('Input such as "rm", "|", "&" are forbidden'))

    name = fields.Char(string='Name', translate=True)
    cmd = fields.Char(string='command root')
    # cmd_params = fields.Char(string='Command params', translate=True)
    params_mandatory = fields.Boolean(string='Has mandatory params')
    description = fields.Text(string='Description', translate=True)
    type = fields.Selection(string='Command type',
                            selection=[('simple', 'Simple'), ('with_parameter', 'With parameter')], translate=True)
    groups = fields.Many2many('res.groups', string='Groups')
    active = fields.Boolean(string='Active', default=True)
    default_parameter = fields.Char(string='Default parameter',
                                    help='name of a configuration parameter used as a default parameter appended to the original command'
                                    )
    command = fields.Char(string='Full command', compute='_compute_command')
    suffix_cmd = fields.Many2one('c1_project_dev.command', string='Suffix command',
                                 help='Is appended at the end of the command')
    in_docker = fields.Boolean(string='Runs user\'s docker container')


class Module(models.Model):
    _name = 'c1_project_dev.module'

    INSTALLED_PACKAGES = []

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        if name:
            args = [('technical_name', operator, name)] + args
        return self.search(args, limit=limit).name_get()

    @api.multi
    def name_get(self):
        return [(mod.id, '%s[%s]' % (mod.name, mod.technical_name)) for mod in self]

    @api.multi
    def _compute_installable(self):
        for record in self:
            if record.python_dependencies:
                # installed_distributions = pip.get_installed_distributions()
                # installed_deps = [i.key for i in installed_distributions]
                try:
                    output = self.env.ref('c1_project_dev.cmd_docker_exec').run('pip freeze')
                    # _logger.info(output)

                    installed_deps = [dep.split('==')[0] for dep in output.split('\n') if
                                      not (dep.startswith('Warning:') or dep.startswith('##') or (dep == ''))]
                    _logger.info(installed_deps)
                except Exception as e:
                    _logger.error(e)
                    installed_deps = []

                module_dependencies = record.python_dependencies.strip().split(',')
                installable = True
                for dep in module_dependencies:
                    # print dep
                    if dep.strip() not in installed_deps:
                        # print '---not installed'
                        installable = False
                        break
                record.installable = installable
            else:
                record.installable = True
        return

    @api.multi
    def install_dependencies(self, no_exception=False):
        for record in self:
            installed_distributions = pip.get_installed_distributions()
            if record.python_dependencies:
                installed_deps = [i.key for i in installed_distributions]
                module_dependencies = record.python_dependencies.strip().split(',')
                for dep in module_dependencies:
                    if dep.strip() not in installed_deps:
                        self.env.ref('c1_project_dev.cmd_docker_pip_install').run(dep.strip(), no_exception)
        return True

    @api.multi
    def _compute_downloaded(self):
        for rec in self:
            rec.downloaded = os.path.exists(
                os.path.join(self.env.user.sudo().personal_addons_path, rec.technical_name)
            )

    @api.multi
    def _compute_onserver_revision(self):
        for rec in self:
            if rec.repository_id:
                try:
                    dest_path = os.path.join(rec.repository_id.system_path, rec.technical_name)
                    local_svn = svn.local.LocalClient(dest_path, username=self.env.user.sudo().svn_account or '',
                                                      password=self.env.user.sudo().svn_password or '')
                    local_info = local_svn.info()
                    rec.onserver_revision = local_info['commit_revision']
                except Exception as e:
                    _logger.exception(e)
                    rec.onserver_revision = -1

    @api.multi
    def _compute_current_downloaded_rev(self):
        for rec in self:
            try:
                destination_path = os.path.join(self.env.user.sudo().personal_addons_path, rec.technical_name)
                local_svn = svn.local.LocalClient(destination_path, username=self.env.user.sudo().svn_account or '',
                                                  password=self.env.user.sudo().svn_password or '')
                local_info = local_svn.info()
                rec.current_downloaded_rev = local_info['commit_revision']
            except Exception as e:
                _logger.exception(e)
                rec.current_downloaded_rev = -1

    @api.depends('repository_id')
    def _compute_authz_file(self):
        for rec in self:
            if rec.repository_id:
                rec.authz_file = '%s/%s/conf/authz' % (rec.repository_id.physical_path, rec.technical_name)

    @api.multi
    def _compute_module_dependencies(self):
        for rec in self:
            if rec.repository_id:
                try:
                    manifest_path = os.path.join(rec.repository_id.system_path, rec.technical_name, '__manifest__.py')
                    if os.path.isfile(manifest_path):
                        f = open(manifest_path, 'rb')
                        try:
                            manifest_data = ast.literal_eval(pycompat.to_native(f.read()))
                            # _logger.info(manifest_path)
                            rec.module_dependencies = ','.join(manifest_data.get('depends', []))
                        except Exception as e1:
                            _logger.exception(e1)
                        finally:
                            f.close()
                except Exception as e:
                    _logger.exception(e)

    @api.multi
    def action_download(self):
        return

    name = fields.Char(string='Name', translate=True)
    repository_id = fields.Many2one('c1_project_dev.repository', string='SVN repository')
    technical_name = fields.Char(string='Technical name')
    installable = fields.Boolean(string='Can be installed', compute='_compute_installable', store=False)
    description = fields.Html(string='Description', translate=True)
    active = fields.Boolean(string='Active', default=True)
    project_id = fields.Many2one('project.project', string='String')
    python_dependencies = fields.Char(string='Python dependencies')
    module_dependencies = fields.Char(string='Module dependencies', compute='_compute_module_dependencies', store=False)
    # python_dependencies_ids = fields.Many2many('c1_project_dev.module_pydep',string='Python dependencies', translate=True)
    # python_dependencies_ids = fields.Many2many('c1_project_dev.module_pydep',string='Python dependencies', translate=True)
    downloaded = fields.Boolean(string='Downloaded', compute='_compute_downloaded',
                                help='If the module has already been downloaded to current user\'s personal path')
    current_downloaded_rev = fields.Integer(string='Downloaded Revision', compute='_compute_current_downloaded_rev')
    onserver_revision = fields.Integer(string='On server revision', compute='_compute_onserver_revision')
    revision_mark_ids = fields.One2many('c1_project_dev.module.review', 'module_id', string='Revision markings')
    authz_file = fields.Char(string='Authz file', compute='_compute_authz_file')


# class ModulePythonDependence(models.Model):
#     _name = 'c1_project_dev.module_pydep'
#
#     @api.multi
#     def name_get(self):
#         return [(dep.id, '%s==%s' % ( dep.name , dep.version)) for dep in self]
#
#     name = fields.Char(string='Name', translate=True)
#     version = fields.Char(string='Version')



class ProjectSVNRepository(models.Model):
    _name = 'c1_project_dev.repository'

    @api.multi
    def _compute_groups(self):
        for rec in self:
            if rec.groupsfile_path:
                html_data = '<dl>'
                with open(rec.groupsfile_path, 'r') as group_file:
                    is_group_file = True
                    for line in group_file:
                        if not is_group_file:
                            is_group_file = line.find('[groups]') >= 0
                            if is_group_file:
                                continue
                        else:
                            pass

                        if is_group_file:
                            if line.startswith('#'):
                                continue
                            if line.count('=') != 1:
                                continue

                            line_data = line.split('=')
                            group_name = line_data[0].strip(' ')
                            # group_content = line_data[1].strip(' ').split(',')
                            group_content = line_data[1]

                            html_data = html_data + '<dt>%s</dt><dd>%s</dd>' % (group_name, group_content)
                html_data = html_data + '</dl>'
                rec.groups_info = html_data

    @api.multi
    def action_clone(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'c1_project_dev.git_clone.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_git_repo_url': self.url,
                'default_destination': self.system_path,
                'default_repository_id': self.id,
            }
        }

    name = fields.Char(string='Name', translate=True)
    url = fields.Char(string='Repository URL')
    physical_path = fields.Char(string='Physical repository path')
    system_path = fields.Char(string='System path')
    # authfile_path = fields.Char(string='Authorization file')
    # groupsfile_path = fields.Char(string='Groups file')
    description = fields.Text(string='Description', translate=True)
    module_ids = fields.One2many('c1_project_dev.module', 'repository_id')
    username = fields.Char(string='Public user login')
    passwd = fields.Char(string='Public user password')
    repository_type = fields.Selection([('svn', 'SVN'), ('git', 'GIT')])
    # groups_info = fields.Html(compute='_compute_groups')
    account_ids = fields.One2many('c1_project_dev.svn_account', 'repo_id', string='Users')


class TransferDetail(models.Model):
    _name = 'c1_project_dev.transfer'
    _description = 'Module transfer information'
    _order = 'date desc, revision desc'

    @api.depends('author')
    def _compute_author_user(self):
        for rec in self:
            ResUsers = self.env['res.users']
            search_domain = [('is_svn_user', '=', True), ('svn_account', '=', rec.author)]
            rec.author_user = ResUsers.search(search_domain, limit=1)

    task_id = fields.Many2one('project.task', string='Task')
    user_id = fields.Many2one('res.users', string='Responsible',
                              help='User who did the transfer', translate=True, default=lambda self: self.env.uid)
    date = fields.Datetime(string='Transfer time', default=fields.Datetime.now)
    log_date = fields.Datetime(string='Log date')
    message = fields.Text(string='Log message', translate=True)
    revision = fields.Integer(string='Revision')
    author = fields.Char(string='Revision author')
    author_user = fields.Many2one('res.users', compute='_compute_author_user',
                                  string='Revison Author(User)',
                                  help='Odoo user related to the author of the revision')
    operation_type = fields.Selection([('transfer', 'Transfer'), ('revert', 'Revert')], string='Operation type',
                                      translate=True)
    tag = fields.Selection([('good', 'Good'), ('bad', 'Bad')], string='Tag')


class DockerContainer(models.Model):
    _name = 'c1_project_dev.docker.container'

    @api.multi
    def action_start(self):
        # self.env.ref('c1_project_dev.cmd_docker_start').run(self.name)
        client = docker.from_env()
        container = client.containers.get(self.name)
        container.start()
        return True

    @api.multi
    def action_stop(self):
        # self.env.ref('c1_project_dev.cmd_docker_stop').run(self.name)
        client = docker.from_env()
        container = client.containers.get(self.name)
        container.stop()
        return True

    @api.multi
    def action_restart(self):
        # self.env.ref('c1_project_dev.cmd_docker_restart').run(self.name)
        client = docker.from_env()
        container = client.containers.get(self.name)
        container.restart()
        return True

    @api.multi
    def _compute_status(self):
        client = docker.from_env()
        # _logger.info(containers)
        # containers = { c['Id'][:12]:c for c in containers}
        # _logger.info(containers)
        for rec in self:
            container = client.containers.get(rec.name)
            if container:
                # _logger.info(container.attrs)
                rec.state = container.attrs['State']['Status']
                rec.image = container.attrs['Config']['Image']
                # rec.containerid = info['Id'][:12]
                '''{
                    u'8069/tcp': [{u'HostPort': u'31009', u'HostIp': u'127.0.0.1'}], 
                    u'8072/tcp': [{u'HostPort': u'32009', u'HostIp': u'127.0.0.1'}]
                }'''
                ports_info = container.attrs['NetworkSettings']['Ports']
                ports_info = ', '.join(
                    ['%s:%s->%s' % (ports_info[p][0]['HostIp'], ports_info[p][0]['HostPort'], p) for p in
                     ports_info.keys()])
                # rec.ports_info = ', '.join([ '%s:%s->%s/%s' % (p['IP'],p['PublicPort'], p['PrivatePort'], p['Type']) for p in container.attrs['NetworkSettings']['Ports'] ])
                rec.ports_info = ports_info

    @api.multi
    def _set_user_id(self):
        Users = self.env['res.users']
        for r in self:
            if not r.user_id:
                continue
            users = Users.sudo().search([('docker_instance_id', '=', r.id)])
            if users:
                users.write({'docker_instance_id': False})
            r.user_id.sudo().docker_instance_id = r.id

    # @api.depends('')
    def _compute_user_id(self):
        Users = self.env['res.users']
        for rec in self:
            user = Users.search([('docker_instance_id', '=', rec.id)], limit=1)
            rec.user_id = user and user.id or False

    def _compute_personal_path(self):
        for rec in self:
            rec.log_path = os.path.join(rec.directory or '', 'log/odoo-server.log')
            rec.addons_path = os.path.join(rec.directory or '', 'trunk')
            rec.data_path = os.path.join(rec.directory or '', 'data')
            rec.enterprise_addons_path = os.path.join(rec.directory or '', 'enterprise')

    user_id = fields.Many2one('res.users', string='Owner', compute='_compute_user_id', store=True, inverse='_set_user_id')
    name = fields.Char(string='Container name', required=True, translate=True)
    containerid = fields.Char(string='Container ID')
    image = fields.Char(string='Image', compute='_compute_status')
    ports_info = fields.Char(string='Ports', compute='_compute_status')
    state = fields.Selection([('running', 'Running'), ('exited', 'Exited'), ('restarting', 'Restarting')],
                             string='Status', compute='_compute_status')
    directory = fields.Char(string='Related directory', required=True)
    log_path = fields.Char(string='Log path', compute='_compute_personal_path')
    addons_path = fields.Char(string='Addons path', compute='_compute_personal_path')
    data_path = fields.Char(string='Data path', compute='_compute_personal_path')
    enterprise_addons_path = fields.Char(string='Enterprise addons path', compute='_compute_personal_path')
    docker_db_suffix = fields.Char(string='Database suffix')
    # new_field_ids = fields.One2many(comodel_name="", inverse_name="", string="", required=False, )


class SvnAccount(models.Model):
    _name = 'c1_project_dev.svn_account'

    # _rec_name = 'svn_account'

    @api.multi
    def name_get(self):
        return [(account.id, '%s[%s]' % (account.sudo().repo_id and account.sudo().repo_id.name, account.svn_account))
                for account in self]

    @api.multi
    def _compute_user_id(self):
        Users = self.env['res.users']
        for rec in self:
            user = Users.search([('svn_account_id', '=', rec.id)], limit=1)
            rec.user_id = user and user.id or False

    @api.multi
    def _set_user_id(self):
        Users = self.env['res.users']
        for r in self:
            if not r.user_id:
                continue

            users = Users.sudo().search([('svn_account_id', '=', r.id)])
            if users:
                users.write({'svn_account_id': False})
            r.user_id.sudo().svn_account_id = r

    svn_account = fields.Char(string='Svn account')
    svn_password = fields.Char(string='Svn account password')
    user_id = fields.Many2one('res.users', string='Owner', compute='_compute_user_id', inverse='_set_user_id')
    repo_id = fields.Many2one('c1_project_dev.repository', string='Repository')


class UserPersonalPath(models.Model):
    _name = 'c1_project_dev.users.path'
    _rec_name = 'root'

    @api.multi
    def _compute_user_id(self):
        Users = self.env['res.users']
        for rec in self:
            user = Users.search([('path_id', '=', rec.id)], limit=1)
            rec.user_id = user and user.id or False

    def _compute_personal_path(self):
        for rec in self:
            rec.log_path = os.path.join(rec.root, 'log/odoo-server.log')
            rec.addons_path = os.path.join(rec.root, 'trunk')

    @api.multi
    def _set_user_id(self):
        Users = self.env['res.users']
        for r in self:
            if not r.user_id:
                continue
            users = Users.sudo().search([('path_id', '=', r.id)])
            if users:
                users.write({'path_id': False})
            r.user_id.sudo().path_id = r.id

    root = fields.Char(string='Root directory', required=True)
    log_path = fields.Char(string='Log path', compute='_compute_personal_path', translate=True)
    addons_path = fields.Char(string='Addons path', compute='_compute_personal_path', translate=True)
    # log_path = fields.Char(string='Log path', compute='_compute_personal_path',translate=True)
    # log_path = fields.Char(string='Log path', compute='_compute_personal_path',translate=True)
    user_id = fields.Many2one('res.users', string='Owner', compute='_compute_user_id', store=True,
                              inverse='_set_user_id')


class BackupFile(models.Model):
    _name = 'c1_project_dev.backup_file'
    _order = 'name desc'

    @api.multi
    def _compute_exists(self):
        for rec in self:
            rec.file_exists = os.path.exists(rec.fullname or '')

    @api.multi
    def _compute_datetime(self):
        for rec in self:
            try:
                # name = rec.name.split('.')[0].split('_')[5]
                rec.date = datetime.strptime(rec.name.split('.')[0], '%Y_%m_%d_%H_%M_%S')
            except:
                pass

    name = fields.Char(string='File name')
    fullname = fields.Char(string='Full file name')
    file_exists = fields.Boolean(string='Exists', compute='_compute_exists', translate=True)
    project_folder = fields.Char(string='Project')
    database = fields.Char(string='Database')
    type = fields.Selection([('file', 'File'), ('folder', 'Folder')], string='Type')
    source = fields.Selection([('production', 'Production Server'), ('user', 'User backups')], string='Source')
    date = fields.Datetime(compute='_compute_datetime', store=True)

    @api.model
    def collect_personal_files(self):
        backup_dir = os.path.join(self.env.user.sudo().personal_data_path or '', 'backups')

        db_dirs = [f for f in os.listdir(backup_dir) if os.path.isdir(os.path.join(backup_dir, f))]
        for database in db_dirs:
            db_dir_path = os.path.join(backup_dir, database)
            if not self.search([('fullname', '=', db_dir_path)], count=1):
                self.create({
                    'name': database,
                    'fullname': db_dir_path,
                    'type': 'folder',
                    'source': 'user'
                })

            # files = [ os.path.normcase(f) for f in os.listdir( os.path.join(backup_dir, project_dir) ) if os.path.splitext(os.path.normcase(f))[1] == 'zip' ]
            files = [os.path.normcase(f) for f in os.listdir(os.path.join(backup_dir, db_dir_path))]
            for file in files:
                # fullname = os.path.join(backup_dir, project_dir)
                fullname = os.path.join(db_dir_path, file)
                if not self.search([('fullname', '=', fullname)], count=1):
                    self.create({
                        'name': file,
                        'database': database,
                        'fullname': fullname,
                        'type': 'file',
                        'source': 'user'
                    })

    @api.model
    def collect_files(self):
        # self.search([('id','!=',False)]).unlink()
        self.search([('id', '!=', False)]).filtered(lambda rec: not rec.file_exists).unlink()
        # backup_dir = self.env['ir.values'].sudo().get_default('res.config.settings', 'db_backup_dir') or ''
        backup_dir = get_setting_value(self, 'db_backup_dir') or ''

        server_dirs = [f for f in os.listdir(backup_dir) if os.path.isdir(os.path.join(backup_dir, f))]
        for server_dir in server_dirs:
            server_dir_path = os.path.join(backup_dir, server_dir)

            project_dirs = [f for f in os.listdir(server_dir_path) if os.path.isdir(os.path.join(server_dir_path, f))]
            for project_dir in project_dirs:
                project_dir_path = os.path.join(server_dir_path, project_dir)
                if not self.search([('fullname', '=', project_dir_path)], count=1):
                    self.create({
                        'name': project_dir,
                        'project_folder': server_dir,
                        'fullname': project_dir_path,
                        'type': 'folder',
                        'source': 'production'
                    })
                # files = [ os.path.normcase(f) for f in os.listdir( os.path.join(backup_dir, project_dir) ) if os.path.splitext(os.path.normcase(f))[1] == 'zip' ]
                files = [os.path.normcase(f) for f in os.listdir(os.path.join(backup_dir, project_dir_path))]
                for file in files:
                    # fullname = os.path.join(backup_dir, project_dir)
                    fullname = os.path.join(project_dir_path, file)
                    if not self.search([('fullname', '=', fullname)], count=1):
                        self.create({'name': file, 'project_folder': project_dir, 'fullname': fullname, 'type': 'file',
                                     'source': 'production'})


class ModuleReviewRecord(models.Model):
    _name = 'c1_project_dev.module.review'

    @api.model
    def rate(self, module_id, revision, rate, comment=None):
        module = self.env['c1_project_dev.module'].search([('id', '=', module_id)], limit=1)
        if not module:
            return False
        return self.create({
            'module_id': module.id,
            'revision': revision,
            'judgement': rate,
            'description': comment,
        })

    @api.model
    def get_last_review(self, module_id, limit=1):
        records = self.sudo().search([('module_id', '=', module_id)], limit=limit, order='create_date DESC')
        res = [{
            'user': {
                'id': re.user_id.id,
                'name': re.user_id.name,
                'partner_id': re.user_id.partner_id.id,
                'avatar_url': '/web/image/res.partner/' + str(re.user_id.partner_id.id) + '/image_small',
            },
            'judgement': re.judgement,
            'revision': re.revision,
            'comment': re.description,
            'date': re.date
        } for re in records]

        return res

    @api.model
    def get_reviews(self, module_id, limit=False):
        records = self.sudo().search([('module_id', '=', module_id)], limit=limit,
                                     order='revision DESC, create_date DESC')
        revs = sorted(set(records.mapped('revision')), reverse = True)
        res = []
        for rev in revs:
            res.append({
                'revision': rev,
                'reviews': [{
                    'user': {
                        'id': re.user_id.id,
                        'name': re.user_id.name,
                        'partner_id': re.user_id.partner_id.id,
                        'avatar_url': '/web/image/res.partner/' + str(re.user_id.partner_id.id) + '/image_small',
                    },
                    'judgement': re.judgement,
                    'revision': re.revision,
                    'comment': re.description,
                    'date': re.date
                } for re in records.filtered(lambda r: r.revision == rev)]
            })
        return res

    module_id = fields.Many2one('c1_project_dev.module', 'Module')
    user_id = fields.Many2one('res.users', 'User', default=lambda self: self.env.uid)
    date = fields.Datetime('Date', default=fields.Datetime.now)
    revision = fields.Integer('Subversion revision')
    judgement = fields.Selection([('good', 'OK'), ('not_good', 'NOT OK')], string='Judgement', translate=True)
    description = fields.Text(string='Raison', translate=True)


class ProductionServer(models.Model):
    _name = 'c1_project_dev.server'
    _description = 'Qitong production server'

    name = fields.Char(string='name')
    container_id = fields.Many2one('c1_project_dev.docker.container', string='Container')
    root = fields.Char('Root path', related='container_id.directory')
    addons_path = fields.Char('Addon path', related='container_id.addons_path')
    log_path = fields.Char('Log path', related='container_id.log_path')
