====================
django-deep-prefetch
====================
Django ``prefetch_related`` ORM method can't prefetch lookups through
``GenericForeginKey``'s. This application solves this problem.

With ``GenericForeignKey`` functionality, it is possible to refer to arbitrary
model. Let's ay we have Like model, which is naturally may refer to many types
of data (blogposts, users, photos, comments, etc).

And so it is desireable to be able to perform such lookups::

    Like.objects.prefetch_related('content_object__followers', 'content_object__people_on_photo')

where ``followers`` is the field of ``User`` model and ```people_on_photo``
the field of ``Photo`` model.

Currently ``.prefetch_related`` will raise an error like
::

    Cannot find field "followers" on Photo object.

because it is assumed that lookups are 'strict', and data for each lookup
belongs to one type.

``django-deep-prefetch`` removes this limitation and makes prefetches for
such lookups possible.

Usage
-----
Create `custom manager`_ for your model using ``DeepPrefetchQuerySet``, ``DeepPrefetchQuerySetMixin``,
``DeepPrefetchManager``, ``DeepPrefetchManagerMixin`` classes from
``deep_prefetch.utils`` module. Then just use ``prefetch_related`` ORM method.

Tests
-----
App passes all tests except one from `prefetch_related` section of
Django own test-suite.
``tests_from_django.PrefetchRelatedTests.test_attribute_error`` fails because
``prefetch_related`` replacement not throws exception in case if field
defined in lookup not found on retrieved object. This is expected -
because ``deep_prefetch`` does not assume that data is of same type -
it not throws exception.
There is also one internal test for case of prefetch of fields of different
models through ``GFK``.

To run tests, install tox_ and call ``tox`` command in project
root directory.

Compatibility
-------------
Currently project is tested and compatible with Python 2.7 and Django 1.4.10.

.. _custom manager: https://docs.djangoproject.com/en/1.4/topics/db/managers/#custom-managers
.. _tox: https://pypi.python.org/pypi/tox