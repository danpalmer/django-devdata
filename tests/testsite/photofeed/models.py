from django.contrib.auth.models import User
from django.db import models


class Photo(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    image_url = models.URLField()
    title = models.CharField(max_length=200)

    lat = models.FloatField()
    lng = models.FloatField()

    created = models.DateTimeField(auto_now_add=True)


class Like(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    photo = models.ForeignKey(Photo, on_delete=models.CASCADE)

    created = models.DateTimeField(auto_now_add=True)


class View(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    photo = models.ForeignKey(Photo, on_delete=models.CASCADE)

    created = models.DateTimeField(auto_now_add=True)
