# coding=utf-8
from contextlib import contextmanager
import logging
import traceback
from time import time

from django.core.signals import request_started
from django.db.backends import BaseDatabaseWrapper
from os.path import dirname, abspath, join, pardir, realpath
from django.db.backends.util import CursorWrapper, logger
import pytest
from deep_prefetch.utils import _prefetch_related_objects
from django.db import reset_queries
import django
import deep_prefetch

verbose_cursor_logger = logging.getLogger('verbose_cursor')

BASE_PATHS = [
    # join(dirname(abspath(__file__)), pardir),
    # dirname(abspath(django.__file__)),
    dirname(abspath(deep_prefetch.__file__))
]

SEP = '    /=' + '='*70 + '=/'

@pytest.fixture
def queryset_monkeypatch(monkeypatch):
    monkeypatch.setattr('django.db.models.query.QuerySet._prefetch_related_objects', _prefetch_related_objects)

def make_verbose_cursor():
    log_list = []

    class VerboseCursorWrapper(CursorWrapper):

        def execute(self, sql, params=()):
            self.set_dirty()
            start = time()
            stack = traceback.extract_stack()
            try:
                return self.cursor.execute(sql, params)
            finally:
                stop = time()
                duration = stop - start
                sql = self.db.ops.last_executed_query(self.cursor, sql, params)

                d = {
                    'sql': sql,
                    'time': "%.3f" % duration,
                    'stack': stack
                }
                self.db.queries.append(d)

                formatted_stack = '\n'.join(
                    traceback.format_list(filter_stack(stack, BASE_PATHS)))


                log_list.append(d)

                verbose_cursor_logger.debug(
                    '{sep}\n{sql}\n{tb}\n{sep}'
                    .format(sep=SEP, sql=sql, tb=formatted_stack)
                )

        def executemany(self, sql, param_list):
            self.set_dirty()
            start = time()
            stack = traceback.extract_stack()
            try:
                return self.cursor.executemany(sql, param_list)
            finally:
                stop = time()
                duration = stop - start
                try:
                    times = len(param_list)
                except TypeError:           # param_list could be an iterator
                    times = '?'
                d = {
                    'sql': sql,
                    'time': "%.3f" % duration,
                    'stack': stack
                }
                self.db.queries.append(d)
                log_list.append(d)
                logger.debug('(%.3f) %s; args=%s' % (duration, sql, param_list),
                extra={'duration': duration, 'sql': sql, 'params': param_list}
            )

    def base_database_wrapper_cursor_patch(self):
        self.validate_thread_sharing()
        cursor = VerboseCursorWrapper(self._cursor(), self)
        return cursor

    return log_list, VerboseCursorWrapper, base_database_wrapper_cursor_patch

@contextmanager
def verbose_cursor():
    old_method = BaseDatabaseWrapper.cursor
    l, _, new_method = make_verbose_cursor()
    request_started.disconnect(reset_queries)
    BaseDatabaseWrapper.cursor = new_method
    yield l
    BaseDatabaseWrapper.cursor = old_method
    request_started.connect(reset_queries)

def filter_stack(l, paths):
    return [e for e in l if any(realpath(path) in realpath(e[0]) for path in paths)]


@pytest.yield_fixture
def verbose_cursor_fxt(request):
    with verbose_cursor() as queries:
        yield queries

    # def finalizer():
    #
    #     print(
    #         (
    #     '{} queries was made!'.format(len(connection.queries)) +
    #     '\n'+'\n'.join(
    #     [
    #         ('\n'+'=*'*35+'\n').join(
    #             [e['sql'],
    #              ''.join(traceback.format_list(filter_stack(e['stack'], BASE_PATHS)[:-1]))
    #             ])
    #         for e in connection.queries
    #     ]
    #     ))
    #     )
    #     connection.queries = []
    #
    # request.addfinalizer(finalizer)