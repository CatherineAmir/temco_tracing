
from odoo import models, fields, api

class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.model
    def create(self, vals):
        attachment = super(IrAttachment, self).create(vals)
        if attachment.res_model == 'res.partner' and attachment.res_id:
            partner = self.env['res.partner'].browse(attachment.res_id)
            partner.message_post(
                body=f'Attachment added: <a href="/web/content/{attachment.id}?download=true">{attachment.name}</a>',
                subject="Attachment Added"
            )
        return attachment

    def write(self, vals):
        res = super(IrAttachment, self).write(vals)
        if self.res_model == 'res.partner':
            partner = self.env['res.partner'].browse(self.res_id)
            partner.message_post(
                body=f'Attachment updated: <a href="/web/content/{self.id}?download=true">{self.name}</a>',
                subject="Attachment Updated"
            )
        return res

    def unlink(self):
        for attachment in self:
            if attachment.res_model == 'res.partner':
                partner = self.env['res.partner'].browse(attachment.res_id)
                partner.message_post(
                    body=f'Attachment removed: {attachment.name}',
                    subject="Attachment Removed"
                )
        return super(IrAttachment, self).unlink()
