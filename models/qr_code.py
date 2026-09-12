import base64
import logging
import secrets

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import human_size

_logger = logging.getLogger(__name__)

TOKEN_NBYTES = 16

# Mimetypes that are safe to render inline in the browser. Anything else is
# served with "Content-Disposition: attachment" to avoid XSS through
# user-uploaded HTML/SVG files.
INLINE_MIMETYPES = {
    'application/pdf',
    'text/plain',
    'text/csv',
}
INLINE_PREFIXES = ('image/', 'audio/', 'video/')
BLOCKED_INLINE_MIMETYPES = {
    'image/svg+xml',
    'text/html',
    'text/xml',
    'application/xml',
    'application/xhtml+xml',
}


class QrCode(models.Model):
    _name = 'qr.code'
    _description = 'QR Code Publication'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    # === BASIC FIELDS === #
    name = fields.Char(
        string='Title',
        required=True,
        tracking=True,
        index='trigram',
    )
    description = fields.Html(
        string='Description',
        sanitize=True,
        help="Shown on the public page, above the file list.",
    )
    active = fields.Boolean(default=True)
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('published', 'Published'),
            ('closed', 'Closed'),
        ],
        string='Status',
        default='draft',
        required=True,
        tracking=True,
        copy=False,
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
        index=True,
    )
    user_id = fields.Many2one(
        comodel_name='res.users',
        string='Responsible',
        default=lambda self: self.env.user,
        tracking=True,
    )

    # === PUBLICATION === #
    access_token = fields.Char(
        string='Access Token',
        required=True,
        copy=False,
        readonly=True,
        index='btree',
        default=lambda self: self._generate_access_token(),
    )
    date_expiration = fields.Datetime(
        string='Expiration Date',
        tracking=True,
        help="If set, the public link will stop working after this date.",
    )
    qr_type = fields.Selection(
        selection=[('file', 'File'), ('url', 'URL')],
        string='Type',
        default='file',
        required=True,
    )
    target_url = fields.Char(
        string='Target URL',
        help="The URL to redirect to when scanning the QR code.",
    )
    public_url = fields.Char(
        string='Public URL',
        compute='_compute_public_url',
    )
    qr_image = fields.Binary(
        string='QR Code',
        compute='_compute_qr_image',
        attachment=False,
    )
    is_expired = fields.Boolean(
        string='Expired',
        compute='_compute_is_expired',
        search='_search_is_expired',
    )

    # === FILES === #
    attachment_ids = fields.Many2many(
        comodel_name='ir.attachment',
        relation='qr_code_ir_attachment_rel',
        column1='qr_code_id',
        column2='attachment_id',
        string='Files',
        copy=False,
    )
    attachment_count = fields.Integer(
        string='Files Count',
        compute='_compute_attachment_count',
        store=True,
    )

    # === STATISTICS === #
    view_count = fields.Integer(
        string='Views',
        default=0,
        readonly=True,
        copy=False,
    )
    last_view_date = fields.Datetime(
        string='Last View',
        readonly=True,
        copy=False,
    )

    _sql_constraints = [
        ('access_token_uniq', 'UNIQUE(access_token)',
         'The access token must be unique!'),
    ]

    # === COMPUTE / DEFAULTS === #
    @api.model
    def _generate_access_token(self):
        """Return a new URL-safe random token."""
        return secrets.token_urlsafe(TOKEN_NBYTES)

    @api.depends('attachment_ids')
    def _compute_attachment_count(self):
        for record in self:
            record.attachment_count = len(record.attachment_ids)

    @api.depends('access_token')
    def _compute_public_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param(
            'web.base.url', ''
        ).rstrip('/')
        for record in self:
            record.public_url = (
                '%s/qr/%s' % (base_url, record.access_token)
                if record.access_token else False
            )

    @api.depends('public_url')
    def _compute_qr_image(self):
        report = self.env['ir.actions.report']
        for record in self:
            record.qr_image = False
            if not record.public_url:
                continue
            try:
                png = report.barcode(
                    'QR', record.public_url,
                    width=512, height=512, humanreadable=0, barLevel='M',
                )
            except Exception:  # noqa: BLE001 - never break the form view
                _logger.warning(
                    "Could not render QR code for qr.code %s", record.id,
                    exc_info=True,
                )
            else:
                record.qr_image = base64.b64encode(png)

    @api.depends('date_expiration')
    def _compute_is_expired(self):
        now = fields.Datetime.now()
        for record in self:
            record.is_expired = bool(
                record.date_expiration and record.date_expiration < now
            )

    def _search_is_expired(self, operator, value):
        if operator not in ('=', '!=') or not isinstance(value, bool):
            raise UserError(_("Unsupported search on 'Expired'."))
        expired_domain = [
            ('date_expiration', '!=', False),
            ('date_expiration', '<', fields.Datetime.now()),
        ]
        if (operator == '=') == bool(value):
            return expired_domain
        return ['|', ('date_expiration', '=', False),
                ('date_expiration', '>=', fields.Datetime.now())]

    # === CRUD === #
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('access_token'):
                vals['access_token'] = self._generate_access_token()
        return super().create(vals_list)

    def copy(self, default=None):
        default = dict(default or {})
        default.setdefault('name', _("%s (copy)") % self.name)
        default.setdefault('access_token', self._generate_access_token())
        default.setdefault('state', 'draft')
        return super().copy(default)

    def unlink(self):
        """Drop the attachments owned exclusively by the deleted records."""
        candidates = self.attachment_ids.filtered(
            lambda a: a.res_model == self._name
        )
        result = super().unlink()
        orphans = candidates.filtered(
            lambda a: not self.sudo().search_count(
                [('attachment_ids', 'in', a.id)]
            )
        )
        orphans.sudo().unlink()
        return result

    # === ACTIONS === #
    def action_publish(self):
        for record in self:
            if record.qr_type == 'file' and not record.attachment_ids:
                raise UserError(
                    _("Add at least one file before publishing '%s'.")
                    % record.name
                )
            if record.qr_type == 'url' and not record.target_url:
                raise UserError(
                    _("A target URL is required before publishing '%s'.")
                    % record.name
                )
        self.write({'state': 'published'})

    def action_close(self):
        self.write({'state': 'closed'})

    def action_back_to_draft(self):
        self.write({'state': 'draft'})

    def action_regenerate_token(self):
        """Invalidate the current URL/QR and issue a new one."""
        for record in self:
            record.access_token = record._generate_access_token()
            record.message_post(
                body=_("Access token regenerated: previous QR codes and links "
                       "no longer work.")
            )

    def action_open_public_page(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '/qr/%s' % self.access_token,
            'target': 'new',
        }

    def action_download_qr(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '/qr/%s/qrcode.png?download=1' % self.access_token,
            'target': 'self',
        }

    # === PUBLIC ACCESS HELPERS === #
    def _is_publicly_accessible(self):
        """Return True when the public page may be served."""
        self.ensure_one()
        return bool(
            self.active
            and self.state == 'published'
            and not self.is_expired
        )

    def _register_view(self):
        """Increment the visit counter. Must be called with sudo()."""
        for record in self:
            record.write({
                'view_count': record.view_count + 1,
                'last_view_date': fields.Datetime.now(),
            })

    @api.model
    def _get_file_kind(self, mimetype):
        """Map a mimetype to a rendering strategy for the public page."""
        mimetype = (mimetype or '').lower()
        if mimetype in BLOCKED_INLINE_MIMETYPES:
            return 'other'
        if mimetype.startswith('image/'):
            return 'image'
        if mimetype.startswith('video/'):
            return 'video'
        if mimetype.startswith('audio/'):
            return 'audio'
        if mimetype == 'application/pdf':
            return 'pdf'
        return 'other'

    @api.model
    def _can_be_inlined(self, mimetype):
        """Return True when the file may be served with an inline disposition."""
        mimetype = (mimetype or '').lower()
        if mimetype in BLOCKED_INLINE_MIMETYPES:
            return False
        return (
            mimetype in INLINE_MIMETYPES
            or mimetype.startswith(INLINE_PREFIXES)
        )

    def _get_public_files(self):
        """Serialize attachments for the public QWeb template."""
        self.ensure_one()
        files = []
        for attachment in self.attachment_ids.sudo():
            base = '/qr/%s/file/%s' % (self.access_token, attachment.id)
            files.append({
                'id': attachment.id,
                'name': attachment.name,
                'mimetype': attachment.mimetype or 'application/octet-stream',
                'kind': self._get_file_kind(attachment.mimetype),
                'size': human_size(attachment.file_size or 0),
                'view_url': base,
                'download_url': '%s?download=1' % base,
            })
        return files
