import logging
_logger = logging.getLogger(__name__)

from odoo import http, _,tools, SUPERUSER_ID
from ...runbot.controllers.frontend import Runbot
from odoo.exceptions import UserError, ValidationError
from odoo.http import request



class AuthSignInUpHome(Runbot):

    @route([
        '/runbot/glances',
        '/runbot/glances/<int:project_id>'
        ], type='http', auth='public', website=True)
    def glances(self, project_id=None, **kwargs):
        project_ids = [project_id] if project_id else request.env['runbot.project'].search([]).ids # search for access rights
        bundles = request.env['runbot.bundle'].search([('sticky', '=', True), ('project_id', 'in', project_ids),('project_id', '!=', 1)])
        pending = self._pending()
        qctx = {
            'pending_total': pending[0],
            'pending_level': pending[1],
            'bundles': bundles,
            'title': 'Glances'
        }
        return request.render("runbot.glances", qctx)