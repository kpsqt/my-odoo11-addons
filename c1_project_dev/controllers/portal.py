# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import babel.messages.pofile
import base64
import datetime
import functools
import glob
import hashlib
import imghdr
import io
import itertools
import jinja2
import json
import logging
import operator
import os
import re
import sys
import time
import zlib

import werkzeug
import werkzeug.utils
import werkzeug.wrappers
import werkzeug.wsgi
from werkzeug.urls import url_decode, iri_to_uri
from xml.etree import ElementTree


import odoo
import odoo.modules.registry
from odoo.api import call_kw, Environment
from odoo.modules import get_resource_path
from odoo.tools import crop_image, topological_sort, html_escape, pycompat
from odoo.tools.translate import _
from odoo.tools.misc import str2bool, xlwt, file_open
from odoo.tools.safe_eval import safe_eval
from odoo import http
from odoo.http import content_disposition, dispatch_rpc, request, \
    serialize_exception as _serialize_exception, Response
from odoo.exceptions import AccessError, UserError
from odoo.models import check_method_name


# loader = jinja2.PackageLoader('odoo.addons.c1_project_dev', "views")
#
# env = jinja2.Environment(loader=loader, autoescape=True)


_logger = logging.getLogger(__name__)

class Feedback(http.Controller):

    @http.route('/projects/requirements', type='http', auth="public", website=True)
    def requirements(self, **kw):
        env = request.env(context=dict(request.env.context, show_address=True, no_tag_br=True))
        # request._cr = None
        # print (kw)
        # d = {'project_type':kw['path']}
        # return env.get_template("requirements_change_form.html").render(d)
        return request.render("c1_project_dev.index_requirements", {
            'project_type': kw.get('path', None),
        })

    @http.route(['/projects/requirements/create'], type='http', auth='public', methods=["POST"], csrf=False)
    def create(self, **post):
        try:
            request.env['project.task'].create({
                'name': post.get("name"),
                'description': post.get("description"),
                'type': 'feedback'
            })
            return http.local_redirect('/projects/requirements/')
        except Exception as e:
            error = "Requirements submission error: %s" % (str(e) or repr(e))
        return env.get_template("requirements_change_form.html").render(error=error)









