# -*- coding: utf-8 -*-
import datetime
import shutil

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

class AssignFeedbackWizard(models.TransientModel):
    _name = 'c1_project_dev.feedback.wizard'

    project_id = fields.Many2one('project.project', 'Project', required=True)
    task_id = fields.Many2one('project.task', 'Feedback', required=True, domain=[('type','=','feedback'),('project_id','=',False)])


    @api.multi
    def button_assign(self):
        self.task_id.write({'project_id':self.project_id.id})
        self.task_id.onchange_project_id()
        return {'type':'ir.actions.act_window.close'}