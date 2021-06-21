from django.db import models


class Turtle(models.Model):
    standing_on = models.ForeignKey("self", on_delete=models.PROTECT, null=True)


class World(models.Model):
    riding_on = models.ForeignKey(Turtle, on_delete=models.PROTECT)
