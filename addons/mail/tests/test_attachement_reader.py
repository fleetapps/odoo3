from odoo.addons.mail.tools.attachment_reader import attachment_read
from odoo.tests.common import TransactionCase


class TestAttachmentReader(TransactionCase):

    def test_attachment_read(self):
        attachment_txt = self.env['ir.attachment'].create({
            'type': 'binary',
            'raw': b'TEST',
            'name': 'file.txt',
            'mimetype': 'text/plain',
        })
        self.assertEqual(attachment_txt.raw, b'TEST')
        self.assertEqual(attachment_read(attachment_txt, 2), b'TE')
