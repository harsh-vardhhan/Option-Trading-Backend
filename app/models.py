from django.db import models

class Instrument:
    def __init__(
        self, exchange, token, parent_token,
        symbol, name, closing_price, expiry,
        strike_price, tick_size, lot_size,
        instrument_type, isin
    ):
        self.exchange = exchange
        self.token = token
        self.parent_token = parent_token
        self.symbol = symbol
        self.name = name
        self.closing_price = closing_price
        self.expiry = expiry
        self.strike_price = strike_price
        self.tick_size = tick_size
        self.lot_size = lot_size
        self.instrument_type = instrument_type
        self.isin = isin