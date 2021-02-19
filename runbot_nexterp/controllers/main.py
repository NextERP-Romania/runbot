
import datetime
import werkzeug
import logging
import functools

import werkzeug.utils
import werkzeug.urls

from werkzeug.exceptions import NotFound, Forbidden

from odoo.addons.http_routing.models.ir_http import slug
from odoo.addons.website.controllers.main import QueryURL

from odoo.http import Controller, Response, request, route as o_route
from odoo.osv import expression

_logger = logging.getLogger(__name__)

from ...runbot.controllers import frontend


def route2(routes, **kw):
    def decorator(f):
        @o_route(routes, **kw)
        @functools.wraps(f)
        def response_wrap(*args, **kwargs):
            projects = request.env['runbot.project'].search([('id','!=',1)])
            more = request.httprequest.cookies.get('more', False) == '1'
            filter_mode = request.httprequest.cookies.get('filter_mode', 'all')
            keep_search = request.httprequest.cookies.get('keep_search', False) == '1'
            cookie_search = request.httprequest.cookies.get('search', '')
            refresh = kwargs.get('refresh', False)
            nb_build_errors = request.env['runbot.build.error'].search_count([('random', '=', True), ('parent_id', '=', False)])
            nb_assigned_errors = request.env['runbot.build.error'].search_count([('responsible', '=', request.env.user.id)])
            kwargs['more'] = more
            kwargs['projects'] = projects

            response = f(*args, **kwargs)
            if isinstance(response, Response):
                if keep_search and cookie_search and 'search' not in kwargs:
                    search = cookie_search
                else:
                    search = kwargs.get('search', '')
                if keep_search and cookie_search != search:
                    response.set_cookie('search', search)

                project = response.qcontext.get('project') or projects[0]

                response.qcontext['projects'] = projects
                response.qcontext['more'] = more
                response.qcontext['keep_search'] = keep_search
                response.qcontext['search'] = search
                response.qcontext['current_path'] = request.httprequest.full_path
                response.qcontext['refresh'] = refresh
                response.qcontext['filter_mode'] = filter_mode
                response.qcontext['qu'] = QueryURL('/runbot/%s' % (slug(project)), path_args=['search'], search=search, refresh=refresh)
                if 'title' not in response.qcontext:
                    response.qcontext['title'] = 'Runbot %s' % project.name or ''
                response.qcontext['nb_build_errors'] = nb_build_errors
                response.qcontext['nb_assigned_errors'] = nb_assigned_errors

            return response
        return response_wrap
    return decorator

frontend.route = route2