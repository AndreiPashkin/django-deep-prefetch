# coding=utf-8
from collections import defaultdict
from django.db.models import Model
from django.db.models.base import ModelBase
from django.db.models.query import get_prefetcher
from django.db.models.sql.constants import LOOKUP_SEP
from itertools import chain, imap, islice, ifilter
from operator import itemgetter
from collections import OrderedDict
import re
from types import NoneType

__author__ = 'Andrew Pashkin <andrew.pashkin@gmx.co.uk>'


DESCRIPTORS = {
    'GenericForeignKey': {
        'single': True,
        'cache_attr': lambda p, d: p.cache_attr
    },
    'GenericRelatedObjectManager': {
        'single': False,
        'cache_attr': lambda p, d: p.prefetch_cache_name
    },
    'SingleRelatedObjectDescriptor': {
        'single': True,
        'cache_attr': lambda p, d: p.cache_name
    },
    'ReverseSingleRelatedObjectDescriptor': {
        'single': True,
        'cache_attr': lambda p, d: p.cache_name
    },
    'RelatedManager': {
        'single': False,
        'cache_attr': lambda p, d: d.related.field.related_query_name()
    },
    'ManyRelatedManager': {
        'single': False,
        'cache_attr': lambda p, d: p.prefetch_cache_name
    }

}


def is_not_none(arg):
    return arg is not None

def setdefaultattr(obj, name, value):
    if not hasattr(obj, name):
        setattr(obj, name, value)
    return getattr(obj, name)

def head(iterable):
    """First element of `iterable`."""
    return next(iter(iterable))

def tail(iterable):
    """All elements of `iterable` except first one."""
    return drop(1, iterable)

def init(iterable):
    return islice(iterable, len(iterable)-1)

def last(iterable):
    try:
        return head(reversed(iterable))
    except StopIteration:
        raise TypeError('Empty list!')

def drop(n, iterable):
    """Drops `n`th element."""
    return islice(iterable, n)

def put(o, container):
    yield o
    for e in container:
        yield e

def concat(iterable):
    """Concatenates all second-level iterables contained in `iterable`"""
    return chain.from_iterable(iterable)

def find(func, iterable):
    return head(ifilter(func, iterable))


def update_buffer(buffer, objects, lookups):
    objects = [(id(o), o) for o in objects]
    try:
        model = objects[0][1].__class__
    except IndexError:
        raise ValueError('"objects" are empty!')
    for lookup in lookups:
        buffer[lookup][model].update(objects)

def get_cache(obj, prefetcher, descriptor, attr):

    try:
        info = DESCRIPTORS[prefetcher.__class__.__name__]
        single = info['single']
        cache_name = info['cache_attr'](prefetcher, descriptor)
        if single:
            return [getattr(obj, cache_name)]
        else:
            return getattr(obj, '_prefetched_objects_cache')[cache_name]
    except AttributeError:
        raise ValueError('Cache is unset!')
    except KeyError:
        import ipdb; ipdb.set_trace()
        raise ValueError

def set_cache(obj, single, cache, cache_name, attr):
    if single and cache:
        obj.__dict__.update({cache_name: cache[0]})
    elif not single:
        cache_qs = getattr(obj, attr).all()
        cache_qs._result_cache = cache
        cache_qs._prefetch_done = True
        setdefaultattr(obj, '_prefetched_objects_cache', {}).update(
            {cache_name: cache_qs})

def tree():
    return defaultdict(tree)




class DefaultOrderedDict(OrderedDict):
    # taken form http://stackoverflow.com/a/6190500/1818608
    def __init__(self, default_factory=None, *a, **kw):
        if default_factory is not None and not callable(default_factory):
            raise TypeError('first argument must be callable')
        OrderedDict.__init__(self, *a, **kw)
        self.default_factory = default_factory

    def __getitem__(self, key):
        try:
            return OrderedDict.__getitem__(self, key)
        except KeyError:
            return self.__missing__(key)

    def __missing__(self, key):
        if self.default_factory is None:
            raise KeyError(key)
        self[key] = value = self.default_factory()
        return value

    def __reduce__(self):
        if self.default_factory is None:
            args = tuple()
        else:
            args = self.default_factory,
        return type(self), args, None, None, self.items()

    def copy(self):
        return self.__copy__()

    def __copy__(self):
        return type(self)(self.default_factory, self)

    def __deepcopy__(self, memo):
        import copy
        return type(self)(self.default_factory,
                          copy.deepcopy(self.items()))
    def __repr__(self, *args, **kwargs):
        return 'OrderedDefaultDict(%s, %s)' % (self.default_factory,
                                        OrderedDict.__repr__(self))

def update_seen(seen, model, attr, single, cache_name, obj, cache):
    seen[model][attr]['single'] = single
    seen[model][attr]['cache_name'] = cache_name
    seen[model][attr]['cache'][obj] = cache

def clip_lookup(lookup):
    return LOOKUP_SEP.join(lookup.split(LOOKUP_SEP)[1:]) or None


def deep_prefetch_related_objects(objects, lookups):
    """
    Helper function for prefetch_related functionality.

    Populates prefetched objects caches for a list of results
    from a QuerySet.

    Differs from :meth:`django.db.models.query.prefetch_related_objects`
    in that that it can prefetch "non-strict" lookups through GFK.

    :param objects: result cache of base queryset.
    :param lookups: list with lookups.
    """

    #How it works
    #------------
    #   - Since data is not of same type - "unit" of data is a model instance
    #     (object), not QuerySet.
    #   - Goals that I was tried to achieve:
    #       - Prefetching 'non-strict' lookups.
    #       - Absence of doubled queries to DB, other redundancy in processing
    #       - and infinite recursions.
    #       - Simplicity of design in comparison with original
    #         `django.db.models.query.prefetch_related_objects`
    #   - Sets are used to avoid duplicates.
    #   - Python's sets distinguish objects by value. But task require
    #     to distinguish objects by id, not by value, because two objects
    #     that are same by value, might be included in two different
    #     querysets, and both of them must be populated with cache.
    #   - BUT fetched cache data for object are distinguished by value.
    #     Rationale is to distinguish unique queries and prevent their
    #     repeated execution. We don't care about "id" of queries, we care
    #     about their value. Composite identifier for query is
    #     object and lookup for which query being constructed.
    #     Only one query exists for one object (by value) and lookup part.
    #     In function there slightly more complex structure than
    #     `obj -> lookup` used for storing data for traversed lookups
    #     (``seen``) - that's done to reduce redundancy in data, but
    #     "primary key" for stroed data is `obj -> lookup`.
    #   - Data flows through `buffer`, during processing.
    #     Objects discovered while traversing DB structure are being added
    #     and processed objects are removed.
    #todo beauty and refactoring

    if len(objects) == 0:
        return # nothing to do

    #lookup -> model -> {(id(obj), obj), ...}
    #id(obj) - because objects must be distinguished by id.
    #DefaultOrederedDict because order of lookups matter,
    #see tests.LookupOrderingTest.test_order of Django test suite.
    buffer = DefaultOrderedDict(lambda: defaultdict(set))

    update_buffer(buffer, objects, reversed(lookups))
    seen = tree()     # model -> attr ->
                      #              single     -> bool
                      #              cache_name -> str
                      #              cache      ->
                      #                         obj -> [cache]

    while True:
        try:
            lookup = last(buffer.keys())
        except TypeError:
            break
        try:
            model, current = buffer[lookup].popitem()
        except KeyError:
            del buffer[lookup]
            continue

        attr = lookup.split(LOOKUP_SEP)[0]

        sample = current.pop()
        current.add(sample)
        _, object = sample
        prefetcher, _, attr_found, _ = get_prefetcher(object, attr)

        #Lookup is not valid for that object, it must be skipped.
        #No exception, because data it is that data is of diffrerent types,
        #so - such situation is normal.
        if not attr_found:
            continue

        if LOOKUP_SEP not in lookup and prefetcher is None:
            raise ValueError("'%s' does not resolve to a item that supports "
                             "prefetching - this is an invalid parameter to "
                             "prefetch_related()." % lookup)

        if prefetcher is None:
            clipped = clip_lookup(lookup)
            if clipped:
                update_buffer(
                    buffer,
                    filter(is_not_none, [getattr(o, attr)
                                         for _, o in current]),
                    [clipped])
            continue

        single = cache_name = None

        to_discard = set()
        for e in current: # no need to query for already prefetched data
            obj = e[1]
            obj_model = obj.__class__
            p, d, _, is_fetched = get_prefetcher(obj, attr)
            cache = None
            if is_fetched: # case of Django internal cache
                cache = get_cache(obj, p, d, attr)
                update_seen(seen, model, attr, single, cache_name, obj, cache)
                to_discard.add(e)
            elif (model in seen and  # case of `seen`
                attr in seen[obj_model] and
                obj in seen[obj_model][attr]['cache']):
                single = seen[obj_model][attr]['single']
                cache_name = seen[obj_model][attr]['cache_name']
                cache = seen[obj_model][attr]['cache'][obj]
                to_discard.add(e)
                set_cache(obj, single, cache, cache_name, attr)
            if cache is not None:              # if data was cached
                clipped = clip_lookup(lookup)  # it still must get
                if clipped:                    # into `buffer`.
                    update_buffer(buffer, cache, [clipped])

        current -= to_discard

        if current:
            prefetch_qs, rel_attr_fn, cur_attr_fn, single, cache_name =       \
            prefetcher.get_prefetch_query_set(
                map(itemgetter(1), current)
            )

            #prefetch lookups from prefetch queries are merged into processing.
            additional_lookups = getattr(prefetch_qs,
                                         '_prefetch_related_lookups', [])

            if additional_lookups:
                setattr(prefetch_qs, '_prefetch_related_lookups', [])
            discovered = list(prefetch_qs)
            lookups_for_discovered = additional_lookups
            clipped_lookup = LOOKUP_SEP.join(lookup.split(LOOKUP_SEP)[1:])
            if len(clipped_lookup) > 0:
                lookups_for_discovered = chain([clipped_lookup],
                                               additional_lookups)
            if lookups_for_discovered:
                update_buffer(buffer, discovered, reversed(list(lookups_for_discovered)))


            rel_to_cur = defaultdict(list)

            for obj in discovered:
                val = rel_attr_fn(obj)
                rel_to_cur[val].append(obj)
            for pair in current: # queried data is set up to objects
                obj = pair[1]
                val = cur_attr_fn(obj)
                cache = rel_to_cur.get(val, [])
                update_seen(seen, model, attr, single, cache_name, obj, cache)
                set_cache(obj, single, cache, cache_name, attr)