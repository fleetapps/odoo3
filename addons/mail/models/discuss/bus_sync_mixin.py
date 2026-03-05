# Part of Odoo. See LICENSE file for full copyright and licensing details.

import copy
from collections import defaultdict

from odoo import models
from odoo.addons.web.models.models import lazymapping
from odoo.addons.mail.tools.discuss import Store


class BusSyncMixin(models.AbstractModel):
    _name = "bus.sync.mixin"
    _description = "Mixin for Bus Sync"

    def _sync_field_names(self, res):
        """
        Fill the field names to sync in res. Override in specific models.
        Keys are bus subchannel or (main channel_id, subchannel) names, values are Store.FieldList to sync.
        """

    def _store_sync_extra_fields(self, res: Store.FieldList):
        """
        Fill extra field names to sync in res. Override in specific models.
        :param res: list of field names that will be sync
        """

    def write(self, vals):
        def get_field_value(record, field_description):
            """Get the value of a field based on its description."""
            if isinstance(field_description, Store.Attr):
                if field_description.predicate and not field_description.predicate(record):
                    return None
            if isinstance(field_description, Store.Relation):
                return field_description._get_value(record).records
            if isinstance(field_description, Store.Attr):
                return field_description._get_value(record)
            return record[field_description]

        def get_vals_by_field_by_store(record):
            """Get the current values of the fields to sync for the given record, organized by store
            in which to put these values."""
            result = defaultdict(dict)
            for field_list_manager in field_list_managers.values():
                for field_list in field_list_manager.field_lists_by_record[record]:
                    for field_description in field_list:
                        result[field_list.store][field_description] = get_field_value(record, field_description)
            return result

        def get_bus_channels(bus_target, record):
            if isinstance(bus_target, tuple):
                field_name, sub_channel = bus_target
                target = record[field_name]
            else:
                target, sub_channel = record, bus_target
            return [(bus_channel, sub_channel) for bus_channel in target._bus_channels()]

        class FieldListManager:
            """Similar API as Store.FieldList but for multiple field lists at once.
            This is necessary because FieldList is tied to a specific Store, and Store is tied
            to a specific (bus_channel, sub_channel), and there can be multiple bus_channel for one
            record depending on the result of _bus_channels()."""

            def __init__(self, records, target):
                self.field_lists_by_record = {
                    record: [
                        Store.FieldList(stores[bus_channel, sub_channel], record)
                        for bus_channel, sub_channel in get_bus_channels(target, record)
                    ]
                    for record in records
                }

            def _field_lists(self):
                """Get all the field lists for all the records."""
                yield from (
                    field_list
                    for field_lists in self.field_lists_by_record.values()
                    for field_list in field_lists
                )

            def attr(self, *args, **kwargs):
                """Forwards attr to the field lists"""
                for field_list in self._field_lists():
                    field_list.attr(*args, **kwargs)

            def extend(self, *args, **kwargs):
                """Forwards extend to the field lists"""
                for field_list in self._field_lists():
                    field_list.extend(*args, **kwargs)

            def one(self, *args, **kwargs):
                """Forwards one to the field lists"""
                for field_list in self._field_lists():
                    field_list.one(*args, **kwargs)

            def many(self, *args, **kwargs):
                """Forwards many to the field lists"""
                for field_list in self._field_lists():
                    field_list.many(*args, **kwargs)

            def from_method(self, *args, **kwargs):
                """Forwards from_method to the field lists"""
                for field_list in self._field_lists():
                    field_list.from_method(*args, **kwargs)

        stores = lazymapping(lambda param: Store(bus_channel=param[0], bus_subchannel=param[1]))
        field_list_managers = lazymapping(lambda target: FieldListManager(self, target))
        self._sync_field_names(field_list_managers)
        old_vals = {record: get_vals_by_field_by_store(record) for record in self}
        result = super().write(vals)
        for record in self:
            for store, vals_by_field in get_vals_by_field_by_store(record).items():
                field_list = Store.FieldList(store, record)
                for field_description, value in vals_by_field.items():
                    if value != old_vals[record][store][field_description]:
                        # Copy to avoid sharing the same Store.Attr for multiple stores/records.
                        # There is no explicit bug without it at the time of writing this comment,
                        # but Store.Attr should not be assumed immutable during its processing.
                        field_list.append(copy.copy(field_description))
                if field_list:
                    field_list.from_method("_store_sync_extra_fields")
                    store.add(record, field_list)
        for store in stores.values():
            store.bus_send()
        return result
