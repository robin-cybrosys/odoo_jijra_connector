# -*- coding: utf-8 -*-
######################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2021-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Robin K (odoo@cybrosys.com)
#
#    This program is under the terms of the Odoo Proprietary License v1.0 (OPL-1)
#    It is forbidden to publish, distribute, sublicense, or sell copies of the Software
#    or modified copies of the Software.
#
#    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
#    IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
#    DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
#    ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
#    DEALINGS IN THE SOFTWARE.
#
########################################################################################
import json

import requests
from requests.auth import HTTPBasicAuth

from odoo import fields, models
from odoo.exceptions import AccessError


class OdooJiraConnector(models.TransientModel):
    _name = 'odoo.jira.connector'
    _description = 'Odoo Jira Connector'

    jira_domain = fields.Char(compute='compute_jira_domain')
    jira_client_id = fields.Char(compute='compute_client_id')
    jira_secret = fields.Char(compute='compute_client_secret')

    # fetching client,api details
    def compute_jira_domain(self):
        # checking connectivity for exception & fetching jira credentials
        try:
            requests.get('https://www.google.com/').status_code
            print("Connected")
        except:
            raise AccessError('You are not connected to the Internet. '
                              'Check your connection and try again.')
        self.jira_domain = self.env['ir.config_parameter'].sudo().get_param(
            'odoo_jira_connector.jira_domain',
        )
        # checking whether domain is provided
        if not self.jira_domain:
            raise AccessError(
                "Please configure Your Jira application Domain.")

    def compute_client_id(self):
        self.jira_client_id = self.env['ir.config_parameter'].sudo().get_param(
            'odoo_jira_connector.jira_client_id',
        )
        if not self.jira_client_id:
            raise AccessError(
                "Please provide the Client ID obtained from Jira.")

    def compute_client_secret(self):
        self.jira_secret = self.env['ir.config_parameter'].sudo().get_param(
            'odoo_jira_connector.jira_client_secret')
        if not self.jira_secret:
            raise AccessError("Please provide the Jira Secret(Api Token.")

    # get response from jira api
    def get_response(self, key, query):
        url = f"https://{self.jira_domain}.atlassian.net/rest/api/3/{key}"
        auth = HTTPBasicAuth(f"{self.jira_client_id}", f"{self.jira_secret}")
        headers = {
            "Accept": "application/json"
        }
        response = requests.request(
            "GET",
            url,
            params=query,
            headers=headers,
            auth=auth
        )
        # print(json.dumps(json.loads(response.text), sort_keys=True, indent=4,
        #                  separators=(",", ": ")))
        return response

    def user_create(self, vals):
        exists_user = self.env['res.users'].search(
            [('login', '=', vals['login'])])
        if not exists_user:
            self.env["res.users"].create(vals)

    def create_project(self, results):
        change_list = []
        results = results
        records = []
        # fetching projects from odoo
        projects = self.env['project.project'].search([])
        for project in projects:
            change_list.append(project.name)
        for res in results:
            if not (res['name']) in change_list:
                records.append(res)
        # print(records, "results_final")
        project_ids = self.env['project.project'].create(records)
        return project_ids

    # project import
    def import_project(self):
        global vals
        records = []
        results = []
        self.import_p_managers()
        # fetching projects-metadata from jira
        response = self.get_response(f"issue/createmeta", query=None)
        for rec in (json.loads(response.text)['projects']):
            records += [{'name': rec['name'],
                         'key': rec['key']
                         }]
        for rec in records:
            query = {
                'jql': 'project =  %s' % rec['key']
            }
            project_settings = self.get_response("search", query)
            setting = [x for x in (json.loads(project_settings.text)['issues'])]
            for item in setting:
                # print(item)
                p_name = (
                    item['fields']['project']['name'])
                p_desc = (
                    item['fields']['description']['content'][0]['content'][0][
                        'text'])
                # p_creator = (item['fields']['creator']['displayName'])
                p_login = (item['fields']['creator']['emailAddress'])
                proj_manager = self.env['res.users'].search(
                    [('login', '=', p_login)])
                results += [
                    {'name': p_name, 'description': p_desc,
                     'user_id': proj_manager.id,
                     }]
        # print(results,"results passing")
        self.create_project(results)

    #  import project managers
    def import_p_managers(self):
        global values
        users = []
        records = []
        # fetching projects-metadata from jira
        response = self.get_response(f"issue/createmeta", query=None)
        for rec in (json.loads(response.text)['projects']):
            records += [{'name': rec['name'],
                         'key': rec['key']
                         }]
        for rec in records:
            query = {
                'jql': 'project =  %s' % rec['key']
            }
            project_settings = self.get_response("search", query)
            setting = [x for x in (json.loads(project_settings.text)['issues'])]
            for item in setting:
                p_creator = (item['fields']['creator']['displayName'])
                p_login = (item['fields']['creator']['emailAddress'])
                users += [{"login": p_login, "name": p_creator}]
                res_list = []
                for i in range(len(users)):
                    if users[i] not in users[i + 1:]:
                        res_list.append(users[i])
                values = res_list[0]
        self.user_create(values)

    # def create_stages(self, stage):
    #     self.env['project.task.type'].create(stage)

    #  import tasks
    def import_issues(self):
        global values, t_stage
        tasks = []
        change_list = []
        records = []
        results = []
        response = self.get_response(f"issue/createmeta", query=None)
        for rec in (json.loads(response.text)['projects']):
            records += [{'name': rec['name'],
                         'key': rec['key']
                         }]
        for rec in records:
            query = {
                'jql': 'project =  %s' % rec['key']
            }
            project_settings = self.get_response("search", query)
            setting = [x for x in (json.loads(project_settings.text)['issues'])]
            for item in setting:
                print(item['fields']['status'])
                p_name = (
                    item['fields']['project']['name'])
                p_login = (item['fields']['creator']['emailAddress'])
                t_summary = (item['fields']['summary'])
                t_duedate = (item['fields']['duedate'])
                # t_stage = (item['fields']['status']['name'])
                # t_assignee = (item['fields']['assignee']['displayName'])
                proj_manager = self.env['res.users'].search(
                    [('login', '=', p_login)])
                results += [
                    {'name': p_name, 'user_id': proj_manager.id,
                     }]
                tasks += [{'p_name': p_name, 'name': t_summary,
                           'date_deadline': t_duedate}]
        for i in results:
            for j in tasks:
                if i['name'] == j['p_name']:
                    i.update({'task_ids': [(0, 0, {'name': j['name'],
                                                   'date_deadline': j[
                                                       'date_deadline']})]})
        for k in tasks:
            del k['p_name']
        projects = self.env['project.project'].search([])
        for project in projects:
            for res in results:
                if res['name'] == project.name:
                    self.env['project.project'].sudo().search(
                        [('name', '=', project.name)]).update(
                        {'task_ids': [(5, 0, 0)]})
                    # self.create_stages(t_stage)
                    self.env['project.project'].sudo().search(
                        [('name', '=', project.name)]).write(res)
