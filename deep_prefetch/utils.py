# coding=utf-8
from django.db.models import Manager
from django.db.models.query import QuerySet
from deep_prefetch.base import deep_prefetch_related_objects


def _prefetch_related_objects(self):
    # This method can only be called once the result cache has been filled.
    deep_prefetch_related_objects(self._result_cache,
                                  self._prefetch_related_lookups)
    self._prefetch_done = True

class DeepPrefetchQuerySetMixin(object):
    pass

DeepPrefetchQuerySetMixin._prefetch_related_objects = _prefetch_related_objects

class DeepPrefetchQuerySet(QuerySet):
    pass

DeepPrefetchQuerySet._prefetch_related_objects = _prefetch_related_objects


def get_query_set(self):
    return DeepPrefetchQuerySet(self.model, using=self.db)


class DeepPrefetchManagerMixin(object):
    pass


DeepPrefetchManagerMixin.get_query_set = get_query_set

class DeepPrefetchManager(Manager):
    pass

DeepPrefetchManager.get_query_set = get_query_set


