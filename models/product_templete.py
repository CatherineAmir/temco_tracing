from odoo import fields, models, api,_,Command
# class SupplierInfo(models.Model):
#     _name = 'product.supplierinfo'
#     _inherit = ['product.supplierinfo','portal.mixin', 'mail.thread', 'mail.activity.mixin']
#     name = fields.Many2one(tracking=True)
#     currency_id = fields.Many2one(tracking=True)
#     min_qty = fields.Float(tracking=True)
#     product_uom = fields.Many2one(tracking=True)
#     price = fields.Float(tracking=True)
#     delay = fields.Integer(tracking=True)
#     product_tmpl_id = fields.Many2one(tracking=True)
#
#     # to track changes in lines
#     def write(self, vals):
#         # print('write func')
#         super().write(vals)
#         self.env.cr.commit()
#         self.env.cr.savepoint()
#         print('vals', vals)
#         if set(vals) & set(self._get_tracked_fields()):
#             self._track_changes(self.product_tmpl_id)
#
#     # to track changes in lines
#     def _track_changes(self, field_to_track):
#         # print('field_to_track', field_to_track)
#         # print('self.message_ids', self.message_ids)
#         if self.message_ids:
#             message_id = field_to_track.message_post(
#                 body = f'Line with Product: {self.product_tmpl_id.name}').id
#             # print("{self.product_id.name}').id",self.product_tmpl_id.name)
#             trackings = self.env['mail.tracking.value'].sudo().search(
#                 [('mail_message_id', '=', self.message_ids[0].id)])
#             for tracking in trackings:
#                 tracking.copy({'mail_message_id': message_id})
#

class ProductTemplete(models.Model):
    _inherit = 'product.template'
    name = fields.Char(tracking=True)
    sale_ok = fields.Boolean(tracking=True)
    purchase_ok = fields.Boolean(tracking=True)
    detailed_type = fields.Selection(tracking=True)
    uom_id = fields.Many2one(tracking=True)
    uom_po_id = fields.Many2one(tracking=True)
    description = fields.Html(tracking=True)
    list_price = fields.Float(tracking=True)
    tandard_price = fields.Float(tracking=True)
    categ_id = fields.Many2one(tracking=True)
    default_code = fields.Char(tracking=True)
    barcode = fields.Char(tracking=True)
    property_account_income_id = fields.Many2one(tracking=True)
    property_account_expense_id = fields.Many2one(tracking=True)
    tracking = fields.Selection(tracking=True)
    use_expiration_date = fields.Boolean(tracking=True)
    expiration_time = fields.Integer(tracking=True)
    use_time = fields.Integer(tracking=True)
    removal_time = fields.Integer(tracking=True)
    alert_time = fields.Integer(tracking=True)
    invoice_policy = fields.Selection(tracking=True)
    # seller_ids = fields.One2many(tracking=True)

    def write(self, vals):
        if 'description' in vals:
            old_description = self.description
            new_description = vals.get('description')
            message = f"Description updated: {old_description} --> {new_description}"
            res = super(ProductTemplete, self).write(vals)
            self.message_post(body = message)
        else:
            res = super(ProductTemplete, self).write(vals)
        return res
    def _mail_track(self, tracked_fields, initial_values):
        changes, tracking_value_ids = super()._mail_track(tracked_fields, initial_values)
        # Many2many tracking
        if len(changes) > len(tracking_value_ids):
            for changed_field in changes:
                if tracked_fields[changed_field]['type'] in ['one2many', 'many2many','many2one']:
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


