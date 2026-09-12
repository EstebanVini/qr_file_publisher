import base64
import logging

from odoo import _, http
from odoo.http import request

_logger = logging.getLogger(__name__)


class QrFilePublisherController(http.Controller):
    """Public endpoints serving the files of a qr.code publication.

    Every route is reachable by anonymous visitors: authorization relies on
    the random ``access_token`` present in the URL, so all ORM access is done
    with ``sudo()`` after the token has been validated.
    """

    # === HELPERS === #
    def _get_publication(self, access_token):
        """Return the published record matching the token, or an empty set."""
        if not access_token:
            return request.env['qr.code'].sudo().browse()
        publication = request.env['qr.code'].sudo().search(
            [('access_token', '=', access_token)], limit=1
        )
        if not publication or not publication._is_publicly_accessible():
            return request.env['qr.code'].sudo().browse()
        return publication

    def _render_error(self, message):
        values = {'error_message': message}
        if 'website' in request.env:
            values['website'] = request.env['website'].get_current_website()
        return request.render(
            'qr_file_publisher.portal_qr_error',
            values,
            status=404,
        )

    # === ROUTES === #
    @http.route(
        ['/qr/<string:access_token>'],
        type='http', auth='public', methods=['GET'], sitemap=False, website=True,
    )
    def qr_public_page(self, access_token, **kwargs):
        """Landing page reached by scanning the QR code."""
        publication = self._get_publication(access_token)
        if not publication:
            return self._render_error(
                _("This link is not available. It may have expired or been "
                  "revoked by its owner.")
            )
        publication._register_view()
        
        if publication.qr_type == 'url':
            return request.redirect(publication.target_url, code=302, local=False)

        files = publication._get_public_files()
        
        # Si la publicación tiene exactamente un archivo, redirigimos directamente a él
        if len(files) == 1:
            return request.redirect(files[0]['view_url'])

        values = {
            'publication': publication,
            'files': files,
        }
        if 'website' in request.env:
            values['website'] = request.env['website'].get_current_website()
        return request.render('qr_file_publisher.portal_qr_publication', values)

    @http.route(
        ['/qr/<string:access_token>/file/<int:attachment_id>'],
        type='http', auth='public', methods=['GET'], sitemap=False,
    )
    def qr_public_file(self, access_token, attachment_id, download=None, **kw):
        """Stream a single file of the publication."""
        publication = self._get_publication(access_token)
        if not publication:
            return request.not_found()

        attachment = publication.attachment_ids.sudo().filtered(
            lambda a: a.id == attachment_id
        )
        if not attachment:
            return request.not_found()

        wants_download = str(download or '').lower() in ('1', 'true', 'yes')

        as_attachment = wants_download or not request.env['qr.code'].sudo(
        )._can_be_inlined(attachment.mimetype)

        try:
            stream = request.env['ir.binary']._get_stream_from(
                attachment, 'raw'
            )
            return stream.get_response(as_attachment=as_attachment)
        except Exception:  # noqa: BLE001 - fall back to a plain response
            _logger.warning(
                "Falling back to plain response for attachment %s",
                attachment.id, exc_info=True,
            )
            disposition = 'attachment' if as_attachment else 'inline'
            return request.make_response(
                base64.b64decode(attachment.datas or b''),
                headers=[
                    ('Content-Type',
                     attachment.mimetype or 'application/octet-stream'),
                    ('Content-Disposition',
                     '%s; filename="%s"' % (disposition, attachment.name)),
                    ('Content-Security-Policy', "default-src 'none'"),
                ],
            )

    @http.route(
        ['/qr/<string:access_token>/qrcode.png'],
        type='http', auth='public', methods=['GET'], sitemap=False,
    )
    def qr_code_image(self, access_token, download=None, **kwargs):
        """Serve the QR code image itself (handy for printing/labels)."""
        publication = request.env['qr.code'].sudo().search(
            [('access_token', '=', access_token)], limit=1
        )
        if not publication or not publication.qr_image:
            return request.not_found()

        wants_download = str(download or '').lower() in ('1', 'true', 'yes')
        disposition = 'attachment' if wants_download else 'inline'
        filename = 'qr-%s.png' % (publication.access_token or 'code')
        return request.make_response(
            base64.b64decode(publication.qr_image),
            headers=[
                ('Content-Type', 'image/png'),
                ('Content-Disposition',
                 '%s; filename="%s"' % (disposition, filename)),
            ],
        )
