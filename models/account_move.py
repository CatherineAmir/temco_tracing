from odoo import models, fields, api,_
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError
from collections import defaultdict

import re
#forbidden fields
INTEGRITY_HASH_MOVE_FIELDS = ('date', 'journal_id', 'company_id')
INTEGRITY_HASH_LINE_FIELDS = ('debit', 'credit', 'account_id', 'partner_id')
class AccountMove(models.Model):
    _inherit = 'account.move'
    sale_employee_name = fields.Char(string='Salesperson', compute='_compute_sale_employee_name',store=True)
    name = fields.Char(string = 'Number', copy = False, compute = '_compute_name_override', store = True,
                       index = True, tracking = True)
    def cancel_invoices(self):
        for record in self:
            record.state = 'cancel'
    @api.depends('move_type', 'state', 'journal_id')
    def _compute_name_override(self):
        print("innnnnnnnsnsnsnnnnnnnnnnnnnnnnnnnnnnn")
        for move in self:
            if move.move_type == 'out_invoice':
                print('innnnnnnnnnnnnnnnnnnnnnnnnnnn1')
                move.name = move.name
            else:
                print("innnnnnnnnnnnnnnnnnnnnnn12222")
                move._compute_name()
    def _post(self, soft=True):
        """Override the `_post` method to include custom logic for 'out_invoice'."""
        # Call the original `_post` method
        result = super(AccountMove, self)._post(soft=soft)
        for move in result:
            if move.move_type == 'out_invoice':
                to_write = {
                    'payment_reference': move.name,  # Use move.name instead of computed reference
                    'line_ids': []
                }
                for line in move.line_ids.filtered(
                        lambda line: line.account_id.user_type_id.type in ('receivable', 'payable')):
                    to_write['line_ids'].append((1, line.id, {'name': move.name}))
                move.write(to_write)

        return result
    @api.onchange('name', 'highest_name')
    def _onchange_name_warning(self):
        if self.move_type == 'out_invoice':
            return
        res = super(AccountMove, self)._onchange_name_warning()
        return res

    # comment partner_bank_id set default to any bank account
    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        self = self.with_company(self.journal_id.company_id)

        warning = {}
        if self.partner_id:
            rec_account = self.partner_id.property_account_receivable_id
            pay_account = self.partner_id.property_account_payable_id
            if not rec_account and not pay_account:
                action = self.env.ref('account.action_account_config')
                msg = _(
                    'Cannot find a chart of accounts for this company, You should configure it. \nPlease go to Account Configuration.')
                raise RedirectWarning(msg, action.id, _('Go to the configuration panel'))
            p = self.partner_id
            if p.invoice_warn == 'no-message' and p.parent_id:
                p = p.parent_id
            if p.invoice_warn and p.invoice_warn != 'no-message':
                # Block if partner only has warning but parent company is blocked
                if p.invoice_warn != 'block' and p.parent_id and p.parent_id.invoice_warn == 'block':
                    p = p.parent_id
                warning = {
                    'title': _("Warning for %s", p.name),
                    'message': p.invoice_warn_msg
                }
                if p.invoice_warn == 'block':
                    self.partner_id = False
                    return {'warning': warning}

        if self.is_sale_document(include_receipts=True) and self.partner_id:
            self.invoice_payment_term_id = self.partner_id.property_payment_term_id or self.invoice_payment_term_id
            new_term_account = self.partner_id.commercial_partner_id.property_account_receivable_id
        elif self.is_purchase_document(include_receipts=True) and self.partner_id:
            self.invoice_payment_term_id = self.partner_id.property_supplier_payment_term_id or self.invoice_payment_term_id
            new_term_account = self.partner_id.commercial_partner_id.property_account_payable_id
        else:
            new_term_account = None

        for line in self.line_ids:
            line.partner_id = self.partner_id.commercial_partner_id

            if new_term_account and line.account_id.user_type_id.type in ('receivable', 'payable'):
                line.account_id = new_term_account

        self._compute_bank_partner_id()
        bank_ids = self.bank_partner_id.bank_ids.filtered(
            lambda bank: bank.company_id is False or bank.company_id == self.company_id)
        # self.partner_bank_id = bank_ids and bank_ids[0]

        # Find the new fiscal position.
        delivery_partner_id = self._get_invoice_delivery_partner_id()
        self.fiscal_position_id = self.env['account.fiscal.position'].get_fiscal_position(
            self.partner_id.id, delivery_id=delivery_partner_id)
        self._recompute_dynamic_lines()
        if warning:
            return {'warning': warning}

    @api.depends('invoice_origin')
    def _compute_sale_employee_name(self):
        for move in self:
            sale_order = self.env['sale.order'].search([('name', '=', move.invoice_origin)], limit=1)
            if sale_order and sale_order.sale_employee:
                move.sale_employee_name = sale_order.sale_employee.name
            else:
                move.sale_employee_name = False

def _unlink_forbid_parts_of_chain(self):
        """ Moves with a sequence number can only be deleted if they are the last element of a chain of sequence.
        If they are not, deleting them would create a gap. If the user really wants to do this, he still can
        explicitly empty the 'name' field of the move; but we discourage that practice.
        """
        # if not self._context.get('force_delete') and not self.filtered(
        #         lambda move: move.name != '/')._is_end_of_seq_chain():
        #     raise UserError(_(
        #         "You cannot delete this entry, as it has already consumed a sequence number and is not the last one in the chain. You should probably revert it instead."
        #     ))

