# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Translate mode',
    'category': 'Hidden',
    'summary': 'Activates translation mode on the whole database',
    'description': """TODO: module description""",
    'depends': ['web'],
    'data': {
        'security/ir.model.access.csv',
        'data/config_parameter.xml',
        'views/translate_ui_settings.xml',
    },
    'assets': {
        'web.assets_backend': [
            'translate_ui/static/src/**/*',
        ],
        'web.assets_frontend': [
            'translate_ui/static/src/**/*',
        ],
    },
    'pre_init_hook': 'pre_init_hook',
    'post_init_hook': 'post_init_hook',
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
