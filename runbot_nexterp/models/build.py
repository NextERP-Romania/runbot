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

class BuildParameters(models.Model):
    _inherit = 'runbot.build.params'

# add also the mailhog
    def _cmd(self, python_params=None, py_version=None, local_only=True, sub_command=None):
        """Return a list describing the command to start the build
        """
        self.ensure_one()
        build = self
        python_params = python_params or []
        py_version = py_version if py_version is not None else build._get_py_version()
        pres=[]
# start mailhog    
        pres.append(['/bin/mailhog8071'])
#/ start mailhog
        for commit_id in self.env.context.get('defined_commit_ids') or self.params_id.commit_ids:
            if not self.params_id.skip_requirements and os.path.isfile(commit_id._source_path('requirements.txt')):
                repo_dir = self._docker_source_folder(commit_id)
                requirement_path = os.path.join(repo_dir, 'requirements.txt')
                pres.append(['sudo', 'pip%s' % py_version, 'install', '-r', '%s' % requirement_path])

        addons_paths = self._get_addons_path()
        (server_commit, server_file) = self._get_server_info()
        server_dir = self._docker_source_folder(server_commit)

        # commandline
        cmd = ['python%s' % py_version] + python_params + [os.path.join(server_dir, server_file)]
        if sub_command:
            cmd += [sub_command]
        cmd += ['--addons-path', ",".join(addons_paths)]
        # options
        config_path = build._server("tools/config.py")
        if grep(config_path, "no-xmlrpcs"):  # move that to configs ?
            cmd.append("--no-xmlrpcs")
        if grep(config_path, "no-netrpc"):
            cmd.append("--no-netrpc")

        command = Command(pres, cmd, [], cmd_checker=build)

        # use the username of the runbot host to connect to the databases
        command.add_config_tuple('db_user', '%s' % pwd.getpwuid(os.getuid()).pw_name)

        if local_only:
            if grep(config_path, "--http-interface"):
                command.add_config_tuple("http_interface", "127.0.0.1")
            elif grep(config_path, "--xmlrpc-interface"):
                command.add_config_tuple("xmlrpc_interface", "127.0.0.1")

        if grep(config_path, "log-db"):
            logdb_uri = self.env['ir.config_parameter'].get_param('runbot.runbot_logdb_uri')
            logdb = self.env.cr.dbname
            if logdb_uri and grep(build._server('sql_db.py'), 'allow_uri'):
                logdb = '%s' % logdb_uri
            command.add_config_tuple("log_db", "%s" % logdb)
            if grep(config_path, 'log-db-level'):
                command.add_config_tuple("log_db_level", '25')

        if grep(config_path, "data-dir"):
            datadir = build._path('datadir')
            if not os.path.exists(datadir):
                os.mkdir(datadir)
            command.add_config_tuple("data_dir", '/data/build/datadir')

        return command



class BuildResult(models.Model):
    _inherit = 'runbot.build'

    def _docker_run(self, **kwargs):
#        _logger.info('###\n'*5+f'_docker_run **kwargs = {kwargs} \n\ntype(kwargs["cmd"])={type(kwargs["cmd"])}\n\n\n')
        cmd=kwargs['cmd']
#        _logger.info('kwargs["cmd"]=kwargs["cmd"]')
        cmd.pres.append(['/bin/mailhog8071'])
        _logger.info('kwargs["cmd"]=kwargs["cmd"]')
#        _logger.info('after put mailhog ###\n'*5+f'_docker_run **kwargs = {kwargs} \n\ntype(kwargs["cmd"])={type(kwargs["cmd"])}\n\n\n')
        res=super()._docker_run( **kwargs)
        return res

    def _local_pg_createdb(self, dbname):
        self._local_pg_dropdb(dbname)
        _logger.debug("createdb %s", dbname)
        restore = False
        bundle = self.params_id.create_batch_id.bundle_id
        if bundle and bundle.restore_db:
            db_template = bundle.restore_db
            if db_template:
                with local_pgadmin_cursor() as local_cr:
                    local_cr.execute(
                        """SELECT datname 
                           FROM pg_catalog.pg_database 
                           WHERE datname = '%s';""" % db_template)
                    res = local_cr.fetchone()
                    if res:
                        db_template = res[0]
                        local_cr.execute(sql.SQL(
                            """CREATE DATABASE {} TEMPLATE %s""").format(sql.Identifier(dbname)),
                            (db_template,))
                        self.env['runbot.database'].create({'name': dbname, 'build_id': self.id})
                        restore = True
        if not restore:
            super()._local_pg_createdb(dbname)
