# Copyright 2021 NextERP Romania
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    'name': 'Runbot NextERP',
    'category': 'Website',
    'summary': 'Runbot NextERP',
    'version': '13.0.1.0.0',
    'description': "Runbot NextERP",
    'author': 'NextERP Romania',
    'depends': ['runbot'],
    'data': [
        'templates/dockerfile.xml',
        'templates/utils.xml',
        'templates/nginx.xml',  # to add mail.xxx.ronbot to go to maihog
        
        'data/runbot_build_config_data.xml',
        'views/bundle_views.xml',
        ],
}
