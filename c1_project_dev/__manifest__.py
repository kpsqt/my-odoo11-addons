# -*- coding: utf-8 -*-
{
    'name': 'Cotong Development Project Management',
    'version': '1.0',
    'category': 'project',
    'summary': '开发项目管理模块',
    'description': '',
    'author': 'Shanghai Cotong Software Co., Ltd.',
    'website': 'https://www.80sERP.com',
    'depends': [
        'project','website'
    ],
    'data': [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/data.xml",
        "views/project_task_form_view.xml",
        "views/res_users.xml",
        "views/config_view.xml",
        "views/wizard.xml",
        'views/project_templates.xml',
    ],
    'qweb': [
        'static/src/xml/c1_project_dev_widgets.xml'
    ],
    'installable': True,
}




