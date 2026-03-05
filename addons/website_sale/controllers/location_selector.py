# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request, route
from .delivery import Delivery


class LocationSelector(Delivery):

    @route('/website_sale/get_pickup_locations', type='jsonrpc', auth='public', website=True)
    def website_sale_get_pickup_locations(self, carrier_id=None, country_id=None, **kwargs):
        """ Fetch the record or the order from the request and return the pickup locations close to a given zip code.

        :param int carrier_id: ID of delivery.carrier
        :param int country_id: ID of res.country
        :return: The close pickup locations data.
        :rtype: dict
        """
        if country_code := request.geoip.country_code:
            country = request.env['res.country'].search([('code', '=', country_code)], limit=1)
        elif country_id:
            country = request.env['res.country'].browse(country_id)
        else:
            country = request.cart.partner_shipping_id.country_id
        carrier = request.env['delivery.carrier'].browse(carrier_id) if carrier_id else request.cart.carrier_id
        return carrier._get_pickup_locations(country=country, **kwargs)

    @route('/website_sale/set_pickup_location', type='jsonrpc', auth='public', website=True)
    def website_sale_set_pickup_location(self, pickup_location_data):
        """ Fetch the order from the request and set the pickup location on the current order.

        :param str pickup_location_data: The JSON-formatted pickup location address.
         :return: The order summary values.
        :rtype: dict
        """
        order_sudo = request.cart
        order_sudo.set_pickup_location(pickup_location_data)
        return self._order_summary_values(order_sudo)
