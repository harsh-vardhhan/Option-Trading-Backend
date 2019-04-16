from django.db import models

class Instrument(models.Model):
    exchange = models.CharField(max_length=40)
    token = models.CharField(max_length=40)
    parent_token = models.CharField(max_length=40)
    symbol = models.CharField(max_length=40)
    name = models.CharField(max_length=40)
    closing_price = models.CharField(max_length=40)
    expiry = models.CharField(max_length=40)
    strike_price = models.CharField(max_length=40)
    tick_size = models.CharField(max_length=40)
    lot_size = models.CharField(max_length=40)
    instrument_type = models.CharField(max_length=40)
    isin = models.CharField(max_length=40)