from django.db import models

class IoTData(models.Model):
    device_id = models.CharField(max_length=50)
    room = models.CharField(max_length=50)
    temperature = models.FloatField()
    gas = models.IntegerField()
    motion = models.CharField(max_length=20)
    status = models.CharField(max_length=20)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.room