import uuid
from django.db import models
from .examination import Examination


class Prescription(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    examination = models.ForeignKey(
        Examination,
        on_delete=models.CASCADE,
        related_name='medicines'
    )
    name = models.CharField(max_length=255)
    morning = models.BooleanField(default=False)
    evening = models.BooleanField(default=False)
    before_meal = models.BooleanField(default=False)
    quantity = models.PositiveIntegerField()
    summary = models.TextField(blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} (Examination: {self.examination_id})"
