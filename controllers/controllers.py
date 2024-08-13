# -*- coding: utf-8 -*-
# from odoo import http


# class TemcoTracing(http.Controller):
#     @http.route('/temco_tracing/temco_tracing', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/temco_tracing/temco_tracing/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('temco_tracing.listing', {
#             'root': '/temco_tracing/temco_tracing',
#             'objects': http.request.env['temco_tracing.temco_tracing'].search([]),
#         })

#     @http.route('/temco_tracing/temco_tracing/objects/<model("temco_tracing.temco_tracing"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('temco_tracing.object', {
#             'object': obj
#         })
