"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
import autofixture
from django.db import connection
from os.path import join, dirname, abspath, pardir
import pytest
from time import time
import traceback

from .models import Like, Comment, Photo, User, SimpleModel, FKModel

import django
import deep_prefetch
from utils import verbose_cursor

BASE_PATHS = [
    # join(dirname(abspath(__file__)), pardir, pardir),
    # dirname(abspath(django.__file__)),
    dirname(abspath(deep_prefetch.__file__))

]


@pytest.mark.django_db
def test_prefetch_through_gfk():
    photo = autofixture.create_one(Photo)
    like = Like.objects.create(content_object=photo)

    comment = Comment.objects.create(content_object=photo)
    user = autofixture.create_one(User)

    photo.people_on_photo.add(user)
    photo.save()

    connection.queries = []
    with verbose_cursor() as queries:
        objects = list(Like.deep
                       .prefetch_related('content_object__people_on_photo',
                                         'content_object__comments'))
        fields = ['people_on_photo', 'comments']
        fetched = []
        for o in objects:
            fetched.append(o)
            fetched.append(o.content_object)
            for f in fields:
                if hasattr(o.content_object, f):
                    fetched.extend(list(getattr(o.content_object, f).all()))
        expected_objects = sorted([like, photo, comment, user])
        actual_objects = sorted(fetched)

        assert expected_objects == actual_objects

        assert len(queries) == len([Like, Photo, Comment, User])


@pytest.mark.django_db
def test_single_seen():
    """If relation is single and if traversed more than once - it fails."""
    simple_model = autofixture.create_one(SimpleModel)
    autofixture.create(FKModel, 3, field_values={'fk': simple_model})

    queryset = FKModel.deep.prefetch_related('fk', 'fk__fks__fk')
    list(queryset)