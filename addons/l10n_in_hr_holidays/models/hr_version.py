# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import timedelta, UTC

from odoo import models


class HrVersion(models.Model):
    _inherit = 'hr.version'

    def _get_version_work_entries_values(self, date_start, date_stop):
        result = super()._get_version_work_entries_values(date_start, date_stop)
        in_versions = self.filtered(lambda version: version.company_id.country_id.code == 'IN')
        if not in_versions:
            return result

        def _to_utc(dt):
            return dt.replace(tzinfo=UTC) if not dt.tzinfo else dt.astimezone(UTC)

        def _get_entry_date(work_entry_vals):
            if entry_date := work_entry_vals.get('date'):
                return entry_date
            if date_start := work_entry_vals.get('date_start'):
                return _to_utc(date_start).date()
            return False

        start_dt = _to_utc(date_start)
        end_dt = _to_utc(date_stop)
        leaves_by_employee = {
            employee.id: leaves
            for employee, leaves in self.env['hr.leave']._read_group(
            domain=[
                ('employee_id', 'in', in_versions.employee_id.ids),
                ('state', '=', 'validate'),
                ('date_from', '<=', end_dt.replace(tzinfo=None)),
                ('date_to', '>=', start_dt.replace(tzinfo=None)),
                ('l10n_in_contains_sandwich_leaves', '=', True),
            ],
            groupby=['employee_id'],
            aggregates=['id:recordset'],
        ) if employee
        }
        if not leaves_by_employee:
            return result

        sandwich_leaves = sum(leaves_by_employee.values(), self.env['hr.leave'])
        indian_leaves, leaves_dates_by_employee, public_holidays_dates_by_company = sandwich_leaves._l10n_in_prepare_sandwich_context()
        span_data = indian_leaves._l10n_in_compute_sandwich_spans(leaves_dates_by_employee, public_holidays_dates_by_company)
        if not span_data:
            return result

        attendance_intervals_by_calendar = {
            calendar: calendar._attendance_intervals_batch(
                start_dt,
                end_dt,
                resources_per_tz=versions._get_resources_per_tz(),
            )
            for calendar, versions in in_versions.grouped('resource_calendar_id').items()
        }
        updatable_entries_by_employee_date = defaultdict(lambda: defaultdict(list))
        occupied_dates_by_employee = defaultdict(set)

        for work_entry_vals in result:
            employee = work_entry_vals.get('employee_id')
            employee_id = employee.id if employee else False
            entry_date = _get_entry_date(work_entry_vals)
            if not employee_id or not entry_date:
                continue
            occupied_dates_by_employee[employee_id].add(entry_date)
            if not work_entry_vals.get('leave_ids'):
                updatable_entries_by_employee_date[employee_id][entry_date].append(work_entry_vals)

        for version in in_versions:
            employee = version.employee_id
            employee_id = employee.id
            calendar = version.resource_calendar_id
            resource = employee.resource_id
            attendance_intervals = attendance_intervals_by_calendar.get(calendar, {}).get(resource.id, [])
            attendance_dates = {interval[0].date() for interval in attendance_intervals}
            occupied_dates = occupied_dates_by_employee[employee_id]
            updatable_entries_by_date = updatable_entries_by_employee_date[employee_id]

            for leave in leaves_by_employee.get(employee_id):
                span_info = span_data.get(leave.id)
                if not span_info or not span_info['has_non_working']:
                    continue

                leave_start_date = max(span_info['start'], start_dt.date())
                leave_end_date = min(span_info['end'], end_dt.date())
                if leave_end_date < leave_start_date:
                    continue

                leave_work_entry_type = leave.work_entry_type_id
                for offset in range((leave_end_date - leave_start_date).days + 1):
                    span_date = leave_start_date + timedelta(days=offset)
                    if updatable_entries := updatable_entries_by_date.pop(span_date, []):
                        for work_entry_vals in updatable_entries:
                            work_entry_vals.update({
                                'work_entry_type_id': leave_work_entry_type,
                                'leave_ids': leave,
                            })
                        continue

                    if span_date in attendance_dates or span_date in occupied_dates:
                        continue

                    result.append({
                        'date': span_date,
                        'duration': calendar.hours_per_day,
                        'work_entry_type_id': leave_work_entry_type,
                        'employee_id': employee,
                        'company_id': version.company_id,
                        'version_id': version,
                        'leave_ids': leave,
                    })
                    occupied_dates.add(span_date)
        return result
