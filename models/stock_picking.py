from odoo import models, fields, api, _
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.exceptions import UserError
from datetime import timedelta ,time
import pytz
class StockMove(models.Model):
    _inherit = 'stock.move'
    actual_date = fields.Datetime(
        string='Actual Date',
        compute='_compute_actual_date',
        store=True,
        readonly=True,
        help="Actual date of the stock operation as per scheduled date in picking"
    )


    def _prepare_account_move_vals(self, credit_account_id, debit_account_id, journal_id, qty, description, svl_id,
                                   cost):


        self.ensure_one()
        # print('inspect _prepare_account_move_vals', inspect.stack()[1].function)

        move_lines = self._prepare_account_move_line(qty, cost, credit_account_id, debit_account_id, description)
        # date = self._context.get('force_period_date', fields.Date.context_today(self))
        date = self.actual_date if self.actual_date else self._context.get('force_period_date', fields.Date.context_today(self))
        # print('date', date)
        # print('move_lines', move_lines)
        return {
            'journal_id': journal_id,
            'line_ids': move_lines,
            'date': date,
            'ref': description,
            'stock_move_id': self.id,
            'stock_valuation_layer_ids': [(6, None, [svl_id])],
            'move_type': 'entry',
        }
    def _prepare_common_svl_vals(self):
        self._compute_actual_date()
        # print('inspect _prepare_common_svl_vals', inspect.stack()[1].function)
        # if self.production_id:
        #     self.actual_date=self.production_id.date_planned_finished
        #     for line in self.production_id.finished_move_line_ids:
        #         line.date=self.production_id.date_planned_finished
        # # print('inspect  self.product_id',  'product_id', self.product_id.name)
        """When a `stock.valuation.layer` is created from a `stock.move`, we can prepare a dict of
        common vals.

        :returns: the common values when creating a `stock.valuation.layer` from a `stock.move`
        :rtype: dict
        """
        self.ensure_one()
        return {
            'stock_move_id': self.id,
            'company_id': self.company_id.id,
            'product_id': self.product_id.id,
            'description': self.reference and '%s - %s' % (self.reference, self.product_id.name) or self.product_id.name,
            'actual_date':self.actual_date
        }

    # Assign actual date to the scheduled date of the transfer
    @api.depends('picking_id')
    def _compute_actual_date(self):
        for move in self:
            if move.picking_id and move.picking_id.scheduled_date:
                move.actual_date = move.picking_id.scheduled_date

    operation_sequence = fields.Integer(
        string="#",
        help="Displays the sequence of the picking type.",
    )

    # Update the function by add = in this condition elif len(move._get_move_lines()) >= 1 to make all operations that have one record or more appear
    @api.depends('product_id', 'has_tracking', 'move_line_ids')
    def _compute_show_details_visible(self):
        """ According to this field, the button that calls `action_show_details` will be displayed
        to work on a move from its picking form view, or not.
        """
        has_package = self.user_has_groups('stock.group_tracking_lot')
        multi_locations_enabled = self.user_has_groups('stock.group_stock_multi_locations')
        consignment_enabled = self.user_has_groups('stock.group_tracking_owner')

        show_details_visible = multi_locations_enabled or has_package

        for move in self:
            move.show_details_visible = True
            # if not move.product_id:
            #     print('sssssssssssssssssssssss')
            #     move.show_details_visible = False
            # elif len(move._get_move_lines()) >= 1:
            #     print('sssssssssaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa')
            #     move.show_details_visible = True
            # else:
            #     move.show_details_visible = (((consignment_enabled and move.picking_code != 'incoming') or
            #                                   show_details_visible or move.has_tracking != 'none') and
            #                                  move._show_details_in_draft() and
            #                                  move.show_operations is False)

class StockPicking(models.Model):
    _inherit = 'stock.picking'
    customer_reference = fields.Char(string="Customer Reference", related='sale_id.client_order_ref', readonly=True)
    sale_customer_id = fields.Many2one(
        'res.partner', string='Customer',readonly=True
    )

    def _compute_set_schedual_date(self):

        cairo_tz = pytz.timezone('Africa/Cairo')
        for picking in self:
            if picking.scheduled_date:
                local_scheduled_date = picking.scheduled_date.astimezone(cairo_tz)
                if local_scheduled_date.time() == time(0, 0):
                    new_date = local_scheduled_date
                else:
                    new_date = local_scheduled_date
                print('Scheduled date:', new_date)
                new_date_naive = new_date.replace(tzinfo=None)
                for move in picking.move_lines:
                    if move.account_move_ids:
                        move.account_move_ids.write({'date': new_date_naive})
    def action_customer(self):
        for picking in self:
            if picking.sale_id:
                picking.sale_customer_id = picking.sale_id.partner_id
            else:
                raise UserError("This picking is not related to any sale order.")
    # override action validate to set date of the accounting date to scheduled date
    def button_validate(self):
        wh_id = self.location_dest_id.warehouse_id
        if wh_id.custom_warehouse_type == 'pre-sale':
            if not self.stamping_done and self.state == 'assigned' and self.picking_type_code not in ['internal',
                                                                                                      'outgoing']:
                raise UserError(_('You can\'t validate until Stamping is checked.'))

        # Clean-up the context key at validation to avoid forcing the creation of immediate
        # transfers.
        ctx = dict(self.env.context)
        ctx.pop('default_immediate_transfer', None)
        self = self.with_context(ctx)

        # Sanity checks.
        pickings_without_moves = self.browse()
        pickings_without_quantities = self.browse()
        pickings_without_lots = self.browse()
        products_without_lots = self.env['product.product']
        for picking in self:
            if not picking.move_lines and not picking.move_line_ids:
                pickings_without_moves |= picking

            picking.message_subscribe([self.env.user.partner_id.id])
            picking_type = picking.picking_type_id
            precision_digits = self.env['decimal.precision'].precision_get('Product Unit of Measure')
            no_quantities_done = all(
                float_is_zero(move_line.qty_done, precision_digits=precision_digits) for move_line in
                picking.move_line_ids.filtered(lambda m: m.state not in ('done', 'cancel')))
            no_reserved_quantities = all(
                float_is_zero(move_line.product_qty, precision_rounding=move_line.product_uom_id.rounding) for move_line
                in picking.move_line_ids)
            if no_reserved_quantities and no_quantities_done:
                pickings_without_quantities |= picking

            if picking_type.use_create_lots or picking_type.use_existing_lots:
                lines_to_check = picking.move_line_ids
                if not no_quantities_done:
                    lines_to_check = lines_to_check.filtered(
                        lambda line: float_compare(line.qty_done, 0, precision_rounding=line.product_uom_id.rounding))
                for line in lines_to_check:
                    product = line.product_id
                    if product and product.tracking != 'none':
                        if not line.lot_name and not line.lot_id:
                            pickings_without_lots |= picking
                            products_without_lots |= product

        if not self._should_show_transfers():
            if pickings_without_moves:
                raise UserError(_('Please add some items to move.'))
            if pickings_without_quantities:
                raise UserError(self._get_without_quantities_error_message())
            if pickings_without_lots:
                raise UserError(_('You need to supply a Lot/Serial number for products %s.') % ', '.join(
                    products_without_lots.mapped('display_name')))
        else:
            message = ""
            if pickings_without_moves:
                message += _('Transfers %s: Please add some items to move.') % ', '.join(
                    pickings_without_moves.mapped('name'))
            if pickings_without_quantities:
                message += _(
                    '\n\nTransfers %s: You cannot validate these transfers if no quantities are reserved nor done. To force these transfers, switch in edit more and encode the done quantities.') % ', '.join(
                    pickings_without_quantities.mapped('name'))
            if pickings_without_lots:
                message += _('\n\nTransfers %s: You need to supply a Lot/Serial number for products %s.') % (
                ', '.join(pickings_without_lots.mapped('name')),
                ', '.join(products_without_lots.mapped('display_name')))
            if message:
                raise UserError(message.lstrip())

        # Run the pre-validation wizards. Processing a pre-validation wizard should work on the
        # moves and/or the context and never call `_action_done`.
        if not self.env.context.get('button_validate_picking_ids'):
            self = self.with_context(button_validate_picking_ids=self.ids)
        res = self._pre_action_done_hook()
        if res is not True:
            return res

        # Call `_action_done`.
        if self.env.context.get('picking_ids_not_to_backorder'):
            pickings_not_to_backorder = self.browse(self.env.context['picking_ids_not_to_backorder'])
            pickings_to_backorder = self - pickings_not_to_backorder
        else:
            pickings_not_to_backorder = self.env['stock.picking']
            pickings_to_backorder = self
        pickings_not_to_backorder.with_context(cancel_backorder=True)._action_done()
        pickings_to_backorder.with_context(cancel_backorder=False)._action_done()
        # Update accounting date with scheduled date
        for picking in self:
            if picking.scheduled_date:
                for move in picking.move_lines:
                    if move.account_move_ids:
                        print("picking.scheduled_date", picking.scheduled_date)
                        move.account_move_ids.sudo().write({'date': picking.scheduled_date})


        if self.user_has_groups('stock.group_reception_report') \
                and self.user_has_groups('stock.group_auto_reception_report') \
                and self.filtered(lambda p: p.picking_type_id.code != 'outgoing'):
            lines = self.move_lines.filtered(lambda
                                                 m: m.product_id.type == 'product' and m.state != 'cancel' and m.quantity_done and not m.move_dest_ids)
            if lines:
                # don't show reception report if all already assigned/nothing to assign
                wh_location_ids = self.env['stock.location']._search(
                    [('id', 'child_of', self.picking_type_id.warehouse_id.view_location_id.id),
                     ('usage', '!=', 'supplier')])
                if self.env['stock.move'].search([
                    ('state', 'in', ['confirmed', 'partially_available', 'waiting', 'assigned']),
                    ('product_qty', '>', 0),
                    ('location_id', 'in', wh_location_ids),
                    ('move_orig_ids', '=', False),
                    ('picking_id', 'not in', self.ids),
                    ('product_id', 'in', lines.product_id.ids)], limit=1):
                    action = self.action_view_reception_report()
                    action['context'] = {'default_picking_ids': self.ids}
                    return action
        return True
    total_product_uom_qty = fields.Float(string='Total Demand : ', compute='_compute_total_product_uom_qty',
                                         store=True)
    total_product_quantity_done = fields.Float(string="Total Done : ", compute='_compute_total_product_qty_done',
                                               store=True)

    # make sequence numbering of the operations when i make new transfer
    @api.onchange('move_ids_without_package')
    def _compute_operation_sequence(self):
        for picking in self:
            sequence = 1
            for move_line in picking.move_ids_without_package.sorted(
                    key=lambda x: (x.location_id.id, x.location_dest_id.id, x.sequence)):
                move_line.operation_sequence = sequence
                sequence += 1

    # calculate total quantity demand of operations in the transfer
    @api.depends('move_ids_without_package.product_uom_qty')
    def _compute_total_product_uom_qty(self):
        for picking in self:
            picking.total_product_uom_qty = sum(move.product_uom_qty for move in picking.move_ids_without_package)

    # calculate total done of operations in transfer
    @api.depends('move_ids_without_package.quantity_done')
    def _compute_total_product_qty_done(self):
        for picking in self:
            picking.total_product_quantity_done = sum(
            move.quantity_done for move in picking.move_ids_without_package)

    # add action to recompute the sequence numbering of the operations
    def recompute_picking_sequence(self):
        for picking in self:
            for index, move in enumerate(picking.move_lines, start=1):
                move.write({'operation_sequence': index})



