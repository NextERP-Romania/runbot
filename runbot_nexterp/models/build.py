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



class BuildResult(models.Model):
    _inherit = 'runbot.build'

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

    def _find_port(self):
        port = super()._find_port()  # next free port started from 2000. is going to be last_used_port +3
        return port + 1


