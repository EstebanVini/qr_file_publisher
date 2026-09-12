import base64

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestQrCode(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.QrCode = cls.env['qr.code']
        cls.attachment = cls.env['ir.attachment'].create({
            'name': 'test.txt',
            'type': 'binary',
            'datas': base64.b64encode(b'hello world'),
            'mimetype': 'text/plain',
        })

    def _create_publication(self, **vals):
        values = {'name': 'Test publication'}
        values.update(vals)
        return self.QrCode.create(values)

    def test_token_is_generated_and_unique(self):
        first = self._create_publication()
        second = self._create_publication()
        self.assertTrue(first.access_token)
        self.assertNotEqual(first.access_token, second.access_token)

    def test_public_url_contains_token(self):
        publication = self._create_publication()
        self.assertIn(publication.access_token, publication.public_url)

    def test_qr_image_is_generated(self):
        publication = self._create_publication()
        self.assertTrue(publication.qr_image)

    def test_publish_requires_files(self):
        publication = self._create_publication()
        with self.assertRaises(UserError):
            publication.action_publish()

    def test_publish_and_accessibility(self):
        publication = self._create_publication(
            attachment_ids=[(6, 0, self.attachment.ids)]
        )
        self.assertFalse(publication._is_publicly_accessible())
        publication.action_publish()
        self.assertEqual(publication.state, 'published')
        self.assertTrue(publication._is_publicly_accessible())
        publication.action_close()
        self.assertFalse(publication._is_publicly_accessible())

    def test_regenerate_token_invalidates_url(self):
        publication = self._create_publication(
            attachment_ids=[(6, 0, self.attachment.ids)]
        )
        old_token = publication.access_token
        publication.action_regenerate_token()
        self.assertNotEqual(old_token, publication.access_token)

    def test_inline_policy(self):
        self.assertTrue(self.QrCode._can_be_inlined('image/png'))
        self.assertTrue(self.QrCode._can_be_inlined('application/pdf'))
        self.assertFalse(self.QrCode._can_be_inlined('image/svg+xml'))
        self.assertFalse(self.QrCode._can_be_inlined('text/html'))
        self.assertFalse(self.QrCode._can_be_inlined('application/zip'))

    def test_file_kind_mapping(self):
        self.assertEqual(self.QrCode._get_file_kind('image/jpeg'), 'image')
        self.assertEqual(self.QrCode._get_file_kind('video/mp4'), 'video')
        self.assertEqual(self.QrCode._get_file_kind('audio/mpeg'), 'audio')
        self.assertEqual(self.QrCode._get_file_kind('application/pdf'), 'pdf')
        self.assertEqual(self.QrCode._get_file_kind('application/zip'), 'other')

    def test_public_files_payload(self):
        publication = self._create_publication(
            attachment_ids=[(6, 0, self.attachment.ids)]
        )
        files = publication._get_public_files()
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0]['name'], 'test.txt')
        self.assertIn(publication.access_token, files[0]['view_url'])
