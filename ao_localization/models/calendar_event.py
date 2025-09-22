"""
@autor: Compllexus
"""

from odoo import fields, models


class HolidayCalendarEvent(models.Model):
    _inherit = 'calendar.event'

    is_public_holiday = fields.Boolean("Is Public Holiday")
