from odoo import models, fields, api,_,Command
from odoo.exceptions import UserError

class SaleOrderLine(models.Model):
    _name = 'sale.order.line'
    _inherit = ['sale.order.line','portal.mixin','mail.thread','mail.activity.mixin']
    product_template_id = fields.Many2one(tracking=True)
    name = fields.Text(tracking=True)
    product_uom_qty = fields.Float(tracking=True)
    product_uom = fields.Many2one(tracking=True)
    price_unit = fields.Float(tracking=True)
    tax_id  = fields.Many2many(tracking=True)
    price_subtotal = fields.Monetary(tracking=True)

    # to track changes in lines
    def write(self, vals):
        # print('write func')
        super().write(vals)
        self.env.cr.commit()
        self.env.cr.savepoint()
        print('vals', vals)
        if set(vals) & set(self._get_tracked_fields()):
            self._track_changes(self.order_id)

    # to track changes in lines
    def _track_changes(self, field_to_track):
        # print('field_to_track', field_to_track)
        # print('self.message_ids', self.message_ids)
        if self.message_ids:
            message_id = field_to_track.message_post(
                body=f'Line with Product: {self.product_template_id.name}').id
            # print("{self.product_id.name}').id",self.product_tmpl_id.name)
            trackings = self.env['mail.tracking.value'].sudo().search(
                [('mail_message_id', '=', self.message_ids[0].id)])
            for tracking in trackings:
                tracking.copy({'mail_message_id': message_id})


class SaleOrder(models.Model):
    _inherit = 'sale.order'
    name = fields.Char(tracking=True)
    order_line = fields.One2many(tracking=True)
    partner_id = fields.Many2one(tracking=True)
    date_order = fields.Datetime(tracking=True)
    custom_date_order =fields.Datetime(tracking=True)
    pricelist_id = fields.Many2one(tracking=True)
    validity_date = fields.Date(tracking=True)
    require_signature = fields.Boolean(tracking=True)
    require_payment = fields.Boolean(tracking=True)
    origin = fields.Char(tracking=True)
    commitment_date = fields.Datetime(tracking=True)
    receipt_reference_number = fields.Many2one(tracking=True)
    payment_term_id = fields.Many2one(tracking=True)
    patient_id = fields.Many2one(tracking=True)
    doctor_id = fields.Many2one(tracking=True)
    sale_user = fields.Many2one(tracking=True)
    sale_employee = fields.Many2one(tracking=True)
    fiscal_position_id = fields.Many2one(tracking=True)
    analytic_account_id = fields.Many2one(tracking=True)
    team_id = fields.Many2one(tracking=True,store=True)
    customer_reference = fields.Char(tracking=True)
    tag_ids = fields.Many2many(tracking=True)
    report_grids = fields.Boolean(tracking=True)
    warehouse_id = fields.Many2one(tracking=True)
    picking_policy = fields.Selection(tracking=True)
    partner_shipping_id = fields.Many2one(tracking=True)
    campaign_id = fields.Many2one(tracking=True)
    medium_id = fields.Many2one(tracking=True)

    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        for order in self:
            customer = order.partner_id
            for picking in order.picking_ids:
                picking.sale_customer_id = customer
        return res

    def action_customer(self):
        for order in self:
            customer = order.partner_id
            for picking in order.picking_ids:
                picking.sale_customer_id = customer
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

    # set partner_bank_id to make it enter manual
    def _prepare_invoice(self):
        """
        Prepare the dict of values to create the new invoice for a sales order. This method may be
        overridden to implement custom invoice generation (making sure to call super() to establish
        a clean extension chain).
        """
        self.ensure_one()
        journal = self.env['account.move'].with_context(default_move_type='out_invoice')._get_default_journal()
        if not journal:
            raise UserError(
                _('Please define an accounting sales journal for the company %s (%s).', self.company_id.name,
                  self.company_id.id))

        invoice_vals = {
            'ref': self.client_order_ref or '',
            'move_type': 'out_invoice',
            'narration': self.note,
            'currency_id': self.pricelist_id.currency_id.id,
            'campaign_id': self.campaign_id.id,
            'medium_id': self.medium_id.id,
            'source_id': self.source_id.id,
            'user_id': self.user_id.id,
            'invoice_user_id': self.user_id.id,
            'team_id': self.team_id.id,
            'partner_id': self.partner_invoice_id.id,
            'partner_shipping_id': self.partner_shipping_id.id,
            'fiscal_position_id': (self.fiscal_position_id or self.fiscal_position_id.get_fiscal_position(
                self.partner_invoice_id.id)).id,
            # 'partner_bank_id': self.company_id.partner_id.bank_ids.filtered(
            #     lambda bank: bank.company_id.id in (self.company_id.id, False))[:1].id,
            'journal_id': journal.id,  # company comes from the journal
            'invoice_origin': self.name,
            'invoice_payment_term_id': self.payment_term_id.id,
            'payment_reference': self.reference,
            'transaction_ids': [(6, 0, self.transaction_ids.ids)],
            'invoice_line_ids': [],
            'company_id': self.company_id.id,
        }
        return invoice_vals