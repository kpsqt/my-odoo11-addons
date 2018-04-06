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

from git import *

class GitWizard(models.TransientModel):
    _name = 'c1_project_dev.git_clone.wizard'

    def _get_branches_selection(self):
        git_url = self.env.context.get('default_git_repo_url')
        # git_repo = Repo("")
        # origin = repo.create_remote('origin', REMOTE_URL)
        # origin.fetch()
        # origin.pull(origin.refs[0].remote_head)
        return

    @api.multi
    def button_clone(self):
        moved = False
        try:
            Module = self.env['c1_project_dev.module']

            if os.path.exists(self.destination):
                shutil.move(self.destination, self.destination+'.bak')
                # shutil.rmtree(self.destination)
                moved = True

            repo = Repo.clone_from(self.git_repo_url or '', self.destination, branch = self.branch or 'master')

            if moved:
                shutil.rmtree(self.destination+'.bak')

            modules = [ f for f in os.listdir(self.destination) if os.path.isdir(os.path.join(self.destination, f))]
            for m in modules:
                module_path = os.path.join(self.destination, m)
                if any(
                        (os.path.isfile(os.path.join(module_path, os.path.normcase(f))) and f in ['__manifest__.py', '__openerp__.py'])
                        for f in os.listdir(module_path)):
                    module = Module.search([('technical_name', '=', m)], limit=1)
                    if not module and self.repository_id:
                        manifest_path = os.path.join(module_path, '__manifest__.py')
                        if not os.path.exists(manifest_path):
                            manifest_path = os.path.join(module_path, '__openerp__.py')
                        manifest_file = open(manifest_path, 'rb')
                        manifest_data = ast.literal_eval(pycompat.to_native(manifest_file.read()))
                        Module.create({
                            'name': manifest_data.get('name', ''),
                            'technical_name': m,
                            'repository_id': self.repository_id.id
                        })

        except Exception as e:
            if moved:
                shutil.move(self.destination+'.bak', self.destination)
            _logger.exception(e)
            raise UserError(e)

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
            'params': {
                'wait': True,
            },
        }


    git_repo_url = fields.Char('Git Url')
    # branches = fields.Selection(selection=_get_branches_selection, string='Branches')
    branch = fields.Char('Branch')
    destination = fields.Char('Destination')
    repository_id = fields.Many2one('c1_project_dev.repository')



