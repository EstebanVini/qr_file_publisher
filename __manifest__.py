{
    'name': 'QR File Publisher',
    'version': '17.0.1.0.0',
    'category': 'Productivity/Documents',
    'summary': 'Generate and publish files or URLs via QR Codes directly from Odoo',
    'description': """
QR File Publisher
=================

Generate and publish files or URLs via QR Codes directly from Odoo.

Key Features:
-------------
* Smart File Publishing & Routing: Attach single or multiple files. Single files open directly; multiple files open a public directory.
* Expiration Dates: Set expiration dates for temporary QR codes.
* Publish Files or Redirect URLs: Use the QR code to share files or simply redirect users to any web page.
* Domain Configuration: Uses the domain specified in Odoo's system parameters (web.base.url).
    """,
    'author': 'Esteban Viniegra Pérez Olagaray',
    'website': 'https://eviniegra.software',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'portal',
    ],
    'data': [
        'security/qr_file_publisher_security.xml',
        'security/ir.model.access.csv',
        'views/qr_code_templates.xml',
        'views/qr_code_views.xml',
        'views/menuitems.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'qr_file_publisher/static/src/scss/qr_public.scss',
        ],
        'web.assets_backend': [
            'qr_file_publisher/static/src/js/file_upload_error.js',
        ],
    },
    'images': ['static/description/banner.jpg', 'static/description/icon.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
