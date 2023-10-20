from contextlib import suppress
from json import decoder

import traceback

from preferences import preferences
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from bot.handlers import bot
from bot.utils import exec_protected
from bot.types import Order
from bot import models
from telebot.types import Update


@csrf_exempt
def update(request):
    try:
        update_json = Update.de_json(request.body.decode())
    except decoder.JSONDecodeError:
        return HttpResponse(b'JSON decode error', status=400)
    # noinspection PyBroadException
    try:
        bot.process_new_updates([update_json])
    except Exception:
        with suppress(Exception):
            bot.send_message(settings.DEVS[0], traceback.format_exc())
    return HttpResponse()


def handle_payment(request):
    order_id = int(request.POST.get('order_id'))
    try:
        order = models.Order.objects.get(id=order_id)
    except models.Order.DoesNotExist:
        return
    order.status = Order.PAYED
    order.save()
    models.Payment.objects.create(user=order.user, amount=float(request.POST.get('price_amount')))


@csrf_exempt
def payment(request):
    exec_protected(handle_payment, request)
