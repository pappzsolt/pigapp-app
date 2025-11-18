from datetime import date, datetime, timedelta

from dateutil import relativedelta
from dateutil.relativedelta import *


class DateFu:

    def get_first_day(self, d_years=0, d_months=0):
        dt = date.today()
        # d_years, d_months are "deltas" to apply to dt
        y, m = dt.year + d_years, dt.month + d_months
        a, m = divmod(m - 1, 12)
        d = date(y + a, m + 1, 1)
        return d

    def getFirstDay(self):
        input_dt = datetime.today()
        res = input_dt.replace(day=1)
        return res.date().strftime('%Y-%m')

    def get_last_day(self):
        return self.get_first_day(0, 1) + timedelta(-1)

    def get_actual_day(self):
        today = date.today()
        return today.strftime('%Y-%m-%d')

    def before_three_months_date(self):
        return date.today() + timedelta(-90)

    def before_two_months_date(self):
        return date.today() + timedelta(-60)

    def get_actual_year_month(self):
        today = date.today()
        return today.strftime('%Y-%m')

    def increment_month(self, d, num):
        return d + relativedelta(months=+num)
