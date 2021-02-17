# Copyright 2021 NextERP Romania
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import logging
import tempfile
import dateutil
import requests
import os
import base64

import odoo
from odoo import models, fields
from odoo.service import db
from odoo.exceptions import UserError
from odoo.addons.runbot.common import local_pgadmin_cursor
from psycopg2 import sql

_logger = logging.getLogger(__name__)


class Repo(models.Model):
    _inherit = 'runbot.repo'

    def _find_new_commits(self, refs, ref_branches):
        """ Overwrite method """
        self.ensure_one()

        for ref_name, sha, date, author, author_email, subject, committer, committer_email in refs:
            branch = ref_branches[ref_name]
            if branch.head_name != sha:  # new push on branch
                _logger.info('repo %s branch %s new commit found: %s', self.name, branch.name, sha)
                commit = self.env['runbot.commit']._get(sha, self.id, {
                    'author': author,
                    'author_email': author_email,
                    'committer': committer,
                    'committer_email': committer_email,
                    'subject': subject,
                    'date': dateutil.parser.parse(date[:19]),
                })
                branch.head = commit
                branch.alive = True
                # Not perfect, il some case a pr can be closed but still visible in repo.
                # The head wont change but on creation the branch will be set alive even if git into said pr is closed
                # It is still better to have false open than false closed
                # NextERP Start
                try:
                    if branch.reference_name and branch.remote_id and branch.remote_id.repo_id._is_branch_forbidden(
                            branch.reference_name):
                        message = "This branch name is incorrect. Branch name should be prefixed with a valid version"
                        message = branch.remote_id.repo_id.invalid_branch_message or message
                        branch.head._github_status(False, "Branch naming", 'failure', False, message)
                except requests.HTTPError as exc:
                    _logger.warning('Error fetching information from Github: %s', exc)
                    # if we start getting 403, this likely means we are hitting
                    # a limit on Github -> stop hammering the service
                    if exc.response.status_code == 403:
                        break
                    # otherwise, we don't have the information we need, it
                    # makes no sense to go on on this ref
                    continue
                # NextERP Stop
                if not self.trigger_ids:
                    continue

                bundle = branch.bundle_id
                if bundle.no_build:
                    continue

                if bundle.last_batch.state != 'preparing' and commit not in bundle.last_batch.commit_ids:
                    preparing = self.env['runbot.batch'].create({
                        'last_update': fields.Datetime.now(),
                        'bundle_id': bundle.id,
                        'state': 'preparing',
                    })
                    bundle.last_batch = preparing

                if bundle.last_batch.state == 'preparing':
                    bundle.last_batch._new_commit(branch)


class Bundle(models.Model):
    _inherit = 'runbot.bundle'

    restore_dump = fields.Many2one("ir.attachment", "Database Dump")
    restore_db = fields.Char('Restore Database')

#    def write(self, vals):
#        res = super().write(vals)
#        if vals.get("restore_dump"):
#            dump = vals.get("restore_dump")
#            attachment = self.env["ir.attachment"].browse(dump)
#            db_name = attachment.name
#            self.restore_db = db_name
#            try:
#                _logger.debug("Delete database %s if exists.", db_name)
#                with local_pgadmin_cursor() as local_cr:
#                    pid_col = 'pid' if local_cr.connection.server_version >= 90200 else 'procpid'
#                    query = 'SELECT pg_terminate_backend({}) ' \
#                            'FROM pg_stat_activity WHERE datname=%s'.format(pid_col)
#                    local_cr.execute(query, [db_name])
#                    local_cr.execute('DROP DATABASE IF EXISTS "%s"' % db_name)
#            except Exception as e:
#                pass
#            try:
#                _logger.debug("Restore new database dump %s.", db_name)
#                data_file = None
#                with tempfile.NamedTemporaryFile(delete=False) as data_file:
#                    data_file.write(base64.b64decode(attachment.datas))
#                    data_file.close()
#                if data_file:
#                    db.restore_db(db_name, data_file.name, True)
#                    self.anonymize_db(db_name)
#            except Exception as e:
#                error = "Database restore error: %s" % (str(e) or repr(e))
#                raise UserError(error)
#            finally:
#                if data_file:
#                    os.unlink(data_file.name)
#        return res

    def anonymize_db(self, db_name):
        with local_pgadmin_cursor() as local_cr:
            local_cr.execute(
                """SELECT datname FROM pg_catalog.pg_database 
                   WHERE datname = '%s';""" % db_name)
            res = local_cr.fetchone()
            if res:
                db_name = res[0]
                registry = odoo.registry(db_name)
                with odoo.api.Environment.manage():
                    with registry.cursor() as db_cr:
                        db_cr.execute(
                            """DELETE from ir_config_parameter where id IN 
                               (SELECT id FROM ir_config_parameter 
                               WHERE key = 'database.enterprise_code');""")
                        db_cr.execute(
                            """UPDATE ir_config_parameter 
                               SET value = (SELECT uuid_in(
                               md5(random()::text || clock_timestamp()::text)::cstring)) 
                               where key = 'database.uuid';""")
                        db_cr.execute(
                            """UPDATE ir_config_parameter 
                            SET value = (SELECT uuid_in(
                            md5(random()::text || clock_timestamp()::text)::cstring)) 
                            where key = 'database.secret';")""")
                        db_cr.execute(
                            """DELETE FROM ir_mail_server;
                               DELETE FROM fetchmail_server;
                               DELETE FROM mail_mail;""")



class ConfigStep(models.Model):
    _inherit = 'runbot.build.config.step'
 
    def _run_run_odoo(self, build, log_path, force=False):
        res = super()._run_run_odoo(build, log_path, force)
        build_port = build.port
        # Add mailhog smtp and port
        _logger.info(res)
        res["cmd"] += ["--smtp-port", "1025"]
        res["exposed_ports"] += [build_port +2]
        return res