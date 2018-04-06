# -*- coding: utf-8 -*-

from odoo.tests import common
import odoo.tests


class TestTask(common.TransactionCase):

    def setUp(self):
        super(TestTask, self).setUp()

        self.Users = self.env['res.users']

        self.group_project_manager_id = self.ref('project.group_project_manager')
        self.group_project_user_id = self.ref('project.group_project_user')
        self.group_user_id = self.ref('base.group_user')

        # Will be used in various test cases of test_hr_flow
        self.demo_user_id = self.ref('base.user_demo')
        self.root_user_id = self.ref('base.user_root')
        # self.main_company_id = self.ref('base.main_company')
        # self.main_partner_id = self.ref('base.main_partner')
        # self.rd_department_id = self.ref('hr.dep_rd')

    @odoo.tests.common.at_install(False)
    @odoo.tests.common.post_install(True)
    def test_some_action(self):
        '''

        :return:
        '''
        print ('#######RUNNING########')
        # record = self.env['model.a'].create({'field': 'value'})
        # record.some_action()
        self.assertEqual(
            True,
            True)
