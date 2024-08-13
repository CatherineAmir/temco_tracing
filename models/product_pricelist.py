from odoo import models, fields, api,_,Command
class ProductPricelistItem(models.Model):
    _name = 'product.pricelist.item'
    _inherit = ['product.pricelist.item','portal.mixin','mail.thread','mail.activity.mixin']
    product_tmpl_id = fields.Many2one(tracking=True)
    product_id = fields.Many2one(tracking=True)
    min_quantity = fields.Float(tracking=True)
    fixed_price = fields.Float(tracking=True)
    date_start = fields.Datetime(tracking=True)
    date_end = fields.Datetime(tracking=True)

    # to track changes in lines
    def write(self, vals):
        # print('write func')
        super().write(vals)
        self.env.cr.commit()
        self.env.cr.savepoint()
        print('vals', vals)
        if set(vals) & set(self._get_tracked_fields()):
            self._track_changes(self.pricelist_id)

    # to track changes in lines
    def _track_changes(self, field_to_track):
        # print('field_to_track', field_to_track)
        # print('self.message_ids', self.message_ids)
        if self.message_ids:
            message_id = field_to_track.message_post(
                body=f'Line with Product: {self.product_tmpl_id.name}').id
            # print("{self.product_id.name}').id",self.product_tmpl_id.name)
            trackings = self.env['mail.tracking.value'].sudo().search(
                [('mail_message_id', '=', self.message_ids[0].id)])
            for tracking in trackings:
                tracking.copy({'mail_message_id': message_id})


class ProductPricelist(models.Model):
    _name = 'product.pricelist'
    _inherit = ['product.pricelist','mail.thread','mail.activity.mixin','portal.mixin']


    name = fields.Char(tracking=True)
    active = fields.Boolean(tracking=True)
    item_ids = fields.One2many(tracking=True, track_visibility='always')
    currency_id = fields.Many2one(tracking=True)
    company_id = fields.Many2one('res.company', 'Company',tracking=True)
    sequence = fields.Integer(tracking=True)
    country_group_ids = fields.Many2many(tracking=True)

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

