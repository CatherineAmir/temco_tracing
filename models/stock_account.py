
from odoo import models, fields, api
class StockAccount(models.Model):
    _inherit = 'stock.valuation.layer'
    actual_date = fields.Datetime(
        string='Actual Date',
        # compute='_compute_actual_date',
        # store=True,
        # readonly=True,
        help="Actual date of the stock operation as per scheduled date in picking"
    )
    # assign the actual date of the transfer to the scheduled date
    # @api.depends('stock_move_id')
    # def _compute_actual_date(self):
    #     for layer in self:
    #         picking = layer.stock_move_id.picking_id
    #         if picking:
    #             layer.actual_date = picking.scheduled_date

