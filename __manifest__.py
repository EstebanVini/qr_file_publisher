{
    'name': 'Creador de Códigos QR',
    'version': '17.0.1.0.0',
    'category': 'Productivity/Documents',
    'summary': 'Publica archivos en la web y compártelos mediante un código QR',
    'description': """
Creador de Códigos QR
=====================

Permite subir archivos de cualquier tipo a una publicación y generar un código
QR que apunta a una página web pública, servida por el propio Odoo, donde los
archivos se pueden visualizar en línea (no se descarga el QR como archivo, el
QR lleva a la web).

Funcionalidades principales:

* Publicaciones con N archivos adjuntos de cualquier tipo.
* Código QR generado con el motor nativo de Odoo (sin dependencias externas).
* Página pública protegida por token aleatorio, con previsualización en línea
  de imágenes, PDF, vídeo, audio y texto.
* Control de estado (borrador / publicado / cerrado), fecha de expiración,
  descarga opcional y contador de visitas.
    """,
    'author': 'Eviniegra Software',
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
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
