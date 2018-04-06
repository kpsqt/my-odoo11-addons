# -*- coding: utf-8 -*-
# Copyright 2016 Onestein (<http://www.onestein.eu>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models

class ProjectIssueStage(models.Model):
    _name = 'project.issue.stage'
    _description = 'Issue Stage'
    _order = 'sequence'

    def _get_default_project_ids(self):
        default_project_id = self.env.context.get('default_project_id')
        return [default_project_id] if default_project_id else None

    name = fields.Char(string='Stage Name', required=True, translate=True)
    description = fields.Text(translate=True)
    sequence = fields.Integer(default=1)
    project_ids = fields.Many2many('project.project',
        'project_issue_stage_rel','issue_stage_id',
        'project_id', string='Projects', default=_get_default_project_ids)
    legend_priority = fields.Char(string='Priority Management Explanation',
        help='''Explanation text to help users using the star and priority mechanism on stages or issues that are in this stage.''')
    legend_blocked = fields.Char(
        string='Kanban Blocked Explanation',
        translate=True,
        help='''Override the default value displayed for the blocked state for kanban selection, when the issue is in that stage.''')
    legend_done = fields.Char(string='Kanban Valid Explanation',
            translate=True,help='''Override the default value displayed for the done state for kanban selection, when the issue is in that stage.''')
    legend_normal = fields.Char(string='Kanban Ongoing Explanation',
            translate=True,help='''Override the default value displayed for the normal state for kanban selection, when the issue is in that stage.''')
    fold = fields.Boolean(string='Folded in Issues Pipeline',help='''This stage is folded in the kanban view when there are no records in that stage to display.''')
    case_default = fields.Boolean(string='Default for New Projects',
        help='''If you check this field, this stage will be proposed by default on each new project. It will not assign this stage to existing projects.''')
    doublon_allowed = fields.Boolean(string='Doublon allowed', help='If this stage can contain many tasks having the same technical name', default=True)
    parent_stage = fields.Many2one('project.issue.stage', string='Precedent stage')
    user_ids = fields.Many2many('res.users', string='Responsible users')
    related_fields = fields.Many2many('ir.model.fields', string='Related fields', domain=[('model_id.model','=','project.issue')])

