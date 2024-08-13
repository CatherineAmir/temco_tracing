from odoo import fields, models, api,Command
# class StockQuant(models.Model):
#     _inherit = 'stock.quant'
#
#     # to track changes in lines
#     def write(self, vals):
#         # print('write func')
#         super().write(vals)
#         self.env.cr.commit()
#         self.env.cr.savepoint()
#         print('vals', vals)
#         if set(vals) & set(self._get_tracked_fields()):
#             self._track_changes(self.order_id)
#
#     # to track changes in lines
#     def _track_changes(self, field_to_track):
#         # print('field_to_track', field_to_track)
#         # print('self.message_ids', self.message_ids)
#         if self.message_ids:
#             message_id = field_to_track.message_post(
#                 body=f'Line with Product: {self.product_template_id.name}').id
#             # print("{self.product_id.name}').id",self.product_tmpl_id.name)
#             trackings = self.env['mail.tracking.value'].sudo().search(
#                 [('mail_message_id', '=', self.message_ids[0].id)])
#             for tracking in trackings:
#                 tracking.copy({'mail_message_id': message_id})


class StockProductionLot(models.Model):
    _inherit = 'stock.production.lot'
    name = fields.Char(tracking=True)
    ref = fields.Char(tracking=True)
    product_id = fields.Many2one(tracking=True)
    product_qty = fields.Float(tracking=True)
    note = fields.Html(tracking=True)
    production_date = fields.Datetime(tracking=True)
    expiration_date = fields.Datetime(tracking=True)
    removal_date = fields.Datetime(tracking=True)
    use_date = fields.Datetime(tracking=True)
    alert_date = fields.Datetime(tracking=True)

    def write(self, vals):
        if 'note' in vals:
            old_note = self.note
            new_note = vals.get('note')
            message = f"Description updated: {old_note} --> {new_note}"
            res = super(StockProductionLot, self).write(vals)
            self.message_post(body=message)
        else:
            res = super(StockProductionLot, self).write(vals)
        return res

    def _mail_track(self, tracked_fields, initial_values):
        changes, tracking_value_ids = super()._mail_track(tracked_fields, initial_values)
        # Many2many tracking
        if len(changes) > len(tracking_value_ids):
            for changed_field in changes:
                if tracked_fields[changed_field]['type'] in ['one2many', 'many2many', 'many2one']:
                    field = self.env['ir.model.fields']._get(self._name, changed_field)
                    vals = {
                        'field': field.id,
                        'field_desc': field.field_description,
                        'field_type': field.ttype,
                        'tracking_sequence': field.tracking,
                        'old_value_char': ', '.join(initial_values[changed_field].mapped('name')),
                        'new_value_char': ', '.join(self[changed_field].mapped('name')),
                    }
                    tracking_value_ids.append(Command.create(vals))
        return changes, tracking_value_ids
