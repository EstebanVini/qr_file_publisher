======================
Creador de Códigos QR
======================

Aplicación para Odoo 17 Community que permite subir archivos de cualquier tipo
y compartirlos mediante un código QR. El QR **no** descarga los archivos: abre
una página web servida por el propio Odoo donde los archivos se visualizan en
línea.

Funcionamiento
==============

1. Instala el módulo y abre la app **Creador de Códigos QR**.
2. Crea una publicación, ponle título y sube los archivos en la pestaña
   *Archivos* (widget ``many2many_binary``, acepta cualquier extensión).
3. Pulsa **Publicar**. Aparecen la URL pública y la imagen del código QR.
4. Comparte o imprime el QR. Al escanearlo se abre
   ``https://<tu-dominio>/qr/<token>``.

Modelo de seguridad
===================

* El acceso público se controla con un token aleatorio de 128 bits
  (``secrets.token_urlsafe``), único por publicación. No hay enumeración por
  ID: la URL no expone el identificador del registro.
* La página solo responde si la publicación está *Publicada*, activa y sin
  fecha de expiración vencida. En cualquier otro caso devuelve un 404.
* **Regenerar enlace** crea un token nuevo e invalida de inmediato todos los
  QR impresos previamente.
* Los archivos se sirven con la cabecera
  ``Content-Security-Policy: default-src 'none'`` (comportamiento por defecto
  de ``odoo.http.Stream``). Los formatos con riesgo de XSS
  (``text/html``, ``image/svg+xml``, XML) nunca se muestran en línea: se
  fuerzan como descarga.
* Solo se previsualizan en línea imágenes, audio, vídeo, PDF y texto plano.
  El resto se ofrece como descarga.
* ``Permitir descarga`` desactivado deja los archivos en modo solo lectura en
  línea (mitigación razonable, no un DRM).

Detalles técnicos
=================

* El QR se genera con ``ir.actions.report.barcode()``, el motor nativo de
  Odoo basado en reportlab. **No requiere dependencias de Python extra**.
  Si tu instalación no tiene ``rlPyCairo`` instalado (dependencia estándar de
  Odoo 16+), la imagen no se generará y verás un aviso en el log; instálalo
  con ``pip install rlPyCairo``.
* Los archivos se sirven con ``ir.binary._get_stream_from()``, lo que soporta
  ``ETag``, peticiones por rangos y el almacenamiento en filestore sin cargar
  el archivo completo en memoria.
* Depende de ``portal`` (no de ``website``), por lo que funciona en bases sin
  el módulo de sitio web instalado. Si usas ``website`` y quieres que las
  páginas hereden el tema, añade ``website=True`` a las rutas del controlador.
* El campo ``qr_image`` es calculado y no almacenado: siempre refleja el token
  y la ``web.base.url`` actuales.

Configuración importante
========================

El parámetro de sistema ``web.base.url`` debe apuntar al dominio público real
(``Ajustes > Técnico > Parámetros del sistema``). Si no, el QR apuntará a
``localhost``. Recomendado también activar ``web.base.url.freeze`` para que
Odoo no lo sobrescriba al iniciar sesión desde otra URL.

Contenido del módulo
====================

::

    qr_file_publisher/
    ├── controllers/main.py          Rutas públicas /qr/<token>
    ├── models/qr_code.py            Modelo qr.code
    ├── security/                    Grupos, reglas de registro y ACL
    ├── views/qr_code_views.xml      Vistas backend (kanban, lista, formulario)
    ├── views/qr_code_templates.xml  Página pública QWeb
    ├── views/menuitems.xml          Menú de la aplicación
    ├── static/src/scss/             Estilos de la página pública
    └── tests/                       Tests unitarios

Créditos
========

Eviniegra Software — Licencia LGPL-3.
