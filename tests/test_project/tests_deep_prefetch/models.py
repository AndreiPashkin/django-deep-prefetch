from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.db import models

# Create your models here.
from deep_prefetch.utils import DeepPrefetchQuerySet


class DeepPrefetchManager(models.Manager):
    def get_query_set(self):
        return DeepPrefetchQuerySet(self.model, using=self.db)

class Like(models.Model):
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveSmallIntegerField()
    content_object = generic.GenericForeignKey()
    objects = models.Manager()
    deep = DeepPrefetchManager()

class Comment(models.Model):
    content_type = models.ForeignKey(ContentType, related_name='comments')
    object_id = models.PositiveSmallIntegerField()
    content_object = generic.GenericForeignKey()

class Photo(models.Model):
    name = models.CharField(max_length=50)
    people_on_photo = models.ManyToManyField('User', related_name='photo_appeared_on')
    comments = generic.GenericRelation(Comment)

class User(models.Model):
    username = models.CharField(max_length=50)
    comments = models.ManyToManyField('Comment')
    photos = models.ManyToManyField('Photo')

class BlogPost(models.Model):
    name = models.CharField(max_length=50)
    author = models.ForeignKey('User', related_name='posts')
    read_by = models.ManyToManyField('User', related_name='read_posts')
    related_posts = models.ManyToManyField('self')
    comments = generic.GenericRelation(Comment)

class SimpleModel(models.Model):
    name = models.CharField(max_length=50)

class FKModel(models.Model):
    name = models.CharField(max_length=50)
    fk = models.ForeignKey('SimpleModel', related_name='fks')
    deep = DeepPrefetchManager()

