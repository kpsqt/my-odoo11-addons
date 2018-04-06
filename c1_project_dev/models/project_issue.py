# -*- coding: utf-8 -*-
# Copyright 2016 Onestein (<http://www.onestein.eu>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import api, fields, models, tools, SUPERUSER_ID, _
from odoo.exceptions import UserError, ValidationError, AccessError


def get_setting_value(self, param):
    return self.env['ir.values'].sudo().get_default(
        'ct_project.config.settings', param)

class ProjectIssue(models.Model):
    _inherit = "project.issue"

    # @api.model
    # def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
    #     res = super(ProjectIssue, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
    #     print '======================================================='
    #     print self
    #     print res.keys()
    #     return res

    # @api.multi
    # def fields_get(self, fields):
    #     print self
    #     print 'fields_get : ', fields
    #     fields_to_hide = ['name','date_deadline','project_id','stage_id']
    #     res = super(ProjectIssue, self).fields_get(fields)
    #     #print res
    #     # for field in fields_to_hide:
    #     #     res[field]['searchable'] = False
    #     #     print res[field]
    #     return res


    @api.model
    def _get_default_issue_stage_id(self):
        return self.issue_stage_find(
            self.env.context.get('default_project_id'),
            [('fold', '=', False)])


    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        active_model = self.env.context.get('active_model')
        active_id = self.env.context.get('active_id')
        if active_model in ['project.project','project.task'] and active_id:
            data = self.env[active_model].search([('id','=',active_id)], limit=1)
            if data and active_model == 'project.project':
                return data.issue_stage_ids
            elif data and active_model == 'project.task':
                if data.project_id:
                    return data.project_id.issue_stage_ids

        if 'default_project_id' in self.env.context:
            data = self.env['project.project'].search([('id', '=', self.env.context.get('default_project_id'))], limit=1)
            if data:
                return data.issue_stage_ids

        if 'default_task_id' in self.env.context:
            data = self.env['project.task'].search([('id', '=', self.env.context.get('default_task_id'))], limit=1)
            if data and data.project_id:
                return data.project_id.issue_stage_ids

        search_domain = []
        stage_ids = stages._search(search_domain, order=order, access_rights_uid=SUPERUSER_ID)
        return stages.browse(stage_ids)


    #task_id = fields.Many2one('project.task', string='Related task')
    technical_name = fields.Char(string='Technical name', related='task_id.technical_name', readonly=True)
    issue_stage_id = fields.Many2one('project.issue.stage',
        string='Issue Stage',
        track_visibility='onchange',
        group_expand='_read_group_stage_ids',
        index=True,
        domain="[('project_ids', '=', project_id)]",
        copy=False,
        default=_get_default_issue_stage_id)
    reopen_description = fields.Html(string='Re-opening Description', translate=True)
    fixing_description = fields.Html(string='Fixing description', translate=True)
    verification_description = fields.Html(string='Verification description', translate=True)
    closing_description = fields.Html(string='Closing description', translate=True)
    cancellation_description = fields.Html(string='Cancellation description', translate=True)



    @api.constrains('issue_stage_id')
    def _check_issue_stage(self):
        #print 'Verifying.....'
        ProjectIssue = self.env['project.issue']
        ProjectIssueStage = self.env['project.issue.stage']
        sensitive_stage_ids = ProjectIssueStage.search([('doublon_allowed', '=', False)]).mapped('id')
        #print 'Sensitive stages: ', sensitive_stage_ids
        for record in self:
            if record.issue_stage_id and record.issue_stage_id.id in sensitive_stage_ids:
                search_domain = [('task_id', '=', record.task_id.id), ('issue_stage_id', '=', record.issue_stage_id.id)]
                #search_domain = [('task_id', '=', record.task_id.id), ('project_id', '=', record.project_id.id), ('issue_stage_id', '=', record.issue_stage_id.id)]
                count = ProjectIssue.search_count(search_domain)
                if count > 1:
                    raise ValidationError(
                        _(
                            "Impossible to have many issues with the same technical name in the stage '%s'" % record.issue_stage_id.name))


    @api.model
    def create(self, vals):
        if 'issue_stage_id' in vals:
            vals.update(self.update_date_closed_issue(vals['issue_stage_id']))
            return super(ProjectIssue, self).create(vals)



    @api.multi
    def write(self, vals):
        IssueStage = self.env['project.issue.stage']
        Wizard = self.env['c1_project_dev.svn_wizard']

        '''
            Checking if the fields to be modified are related to some stages
            and if the user has the right to modify the fields related to the current stage:
            foreach stage:
                    check if one of the fields to be modified related to the stage
                    if related to the stage, check if the user is one of the allowed users to manage the stage
        '''
        for stage in self.project_id.issue_stage_ids:
            stage_related_fields = set(stage.mapped('related_fields.name'))
            stage_related_users = set(stage.mapped('user_ids.id'))
            if bool(len(stage_related_fields.intersection(set(vals.keys())))) and (
                self.env.uid not in stage_related_users):
                raise AccessError(_(
                    'The current user is not authorized to perform this action. Make sure the user has access rights on the fields related to the stage "%s"') % stage.name)


        if 'issue_stage_id' in vals:
            vals.update(self.update_date_closed_issue(vals['issue_stage_id']))
            vals['date_last_stage_update'] = fields.Datetime.now()
            if 'kanban_state' not in vals:
                vals['kanban_state'] = 'normal'

            if self.env.context.get('from_ui', False):
                upload_stage = get_setting_value(self, 'ct_project_issue_upload_stage')
                previous_stage = self.issue_stage_id
                new_stage = IssueStage.search([('id', '=', vals['issue_stage_id'])], limit=1)
                # print 'Previous Stage sequence: ', previous_stage.sequence
                # print 'New Stage sequence: ', new_stage.sequence
                if new_stage and new_stage.id == upload_stage:
                    wizard = Wizard.with_context(
                        default_name = self.technical_name,
                        default_sender_svn_account = self.env.user.svn_account,
                        default_sender_svn_password = self.env.user.svn_password,
                        default_svn_repository = self.task_id.project_id.repository_url,
                        default_task_id = self.task_id
                    ).create({'update_stage':False})
                    wizard.execute_py_svn()
                elif (previous_stage and previous_stage.id == upload_stage) and (new_stage.sequence < previous_stage.sequence):
                    # print '''revert the module to the previous transfer revision'''
                    wizard = Wizard.with_context(
                        default_name = self.technical_name,
                        default_sender_svn_account = self.env.user.svn_account,
                        default_sender_svn_password = self.env.user.svn_password,
                        default_svn_repository = self.project_id.repository_url,
                        default_revision = self.task_id.last_transfer_revision,
                        #current_stage = self.stage_id,
                        default_task_id = self.task_id
                    ).create({'update_stage':False, 'state':'revert'})
                    wizard.execute_py_svn()

        return super(ProjectIssue, self).write(vals)


    def update_date_closed_issue(self, issue_stage_id):
        IssueStage = self.env['project.issue.stage']
        project_issue_stage = IssueStage.browse(issue_stage_id)
        if project_issue_stage.fold:
            return {'date_closed': fields.Datetime.now()}
        return {'date_closed': False}


    def issue_stage_find(self, project_id, domain=None, order='sequence'):
        search_domain = list(domain) if domain else []
        if project_id:
            search_domain += [('project_ids', '=', project_id)]
        project_issue_stage = self.env['project.issue.stage'].search(
                search_domain,
                order=order,
                limit=1)
        return project_issue_stage


    @api.multi
    def _track_template(self, tracking):
        self.ensure_one()
        res = super(ProjectIssue, self)._track_template(tracking)
        res.pop('stage_id', None)
        return res


    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'issue_stage_id' in init_values:
            if self.issue_stage_id:
                if self.issue_stage_id.sequence <= 1:  # start stage -> new
                    return 'project_issue.mt_issue_new'
        if 'issue_stage_id' in init_values:
            return 'project_issue.mt_issue_stage'
        return super(ProjectIssue, self)._track_subtype(init_values)
