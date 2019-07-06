from channels.generic.websocket import AsyncWebsocketConsumer
from upstox_api.api import Session, Upstox, LiveFeedType
import json
import asyncio
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from app.models import Full_Quote
import time
import itertools as it
from django.core.cache import cache
from rq import Queue
from worker import conn
from app.background_process import live_feed_queue
import redis
import os
from django.db import connection
import pdb
import threading

redis_url = os.getenv('REDISTOGO_URL', 'redis://localhost:6379')
r = redis.from_url(redis_url)
api_key = 'Qj30BLDvL96faWwan42mT45gFHyw1mFs8JxBofdx'


def start_subscription():
   symbols = ['nifty', 'banknifty']
   start_time = time.time()

   q = Queue(connection=conn)
   for symbol in symbols:
      for key in r.scan_iter(symbol+"*"):
         access_token = r.get("access_token").decode("utf-8")
         instrument = key.decode('utf-8')
         q.enqueue(live_feed_queue, access_token,'NSE_FO', instrument)


   



