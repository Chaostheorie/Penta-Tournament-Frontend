from app import db, cron
from datetime import date, timedelta
from flask import request
import functools


def requeries_json_keys(keys):
    def actual_decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            data = request.get_json()
            if len([rkey for rkey in keys
                    if rkey not in data]) >= 1:
                return abort(400)
            return func(*args, **kwargs)
        return wrapper
    return actual_decorator


def vacuum_db():
    """
    Runs vacuum at Database
    https://stackoverflow.com/questions/2128336/what-does-it-mean-to-vacuum-a-database
    """
    with db.engine.begin() as conn:
        conn.execute("VACUUM")


def tomorrow():
    """Returns date object for tomorrow"""
    return date.today() + timedelta(days=1)


def schuedle_maintenance():
    """schuedles Maintenance"""
    return cron.add_job(utils.maintenance, "date", date=utils.tomorrow())
