import json
import traceback
import requests
from contextlib import suppress
from django.conf import settings
from preferences import preferences
from telebot.types import ReplyKeyboardMarkup as RKM, InlineKeyboardMarkup as IKM
from telebot.types import KeyboardButton, ReplyKeyboardRemove, InlineKeyboardButton, CallbackQuery
from telebot.apihelper import ApiTelegramException
from bot import models, misc
from bot.utils_lib import helper, callback_data
from bot.types import Order


class States(helper.Helper):
    mode = helper.HelperMode.lowercase
    ORDER_LOG = helper.Item()
    ORDER_PASS = helper.Item()
    ORDER_SHOP = helper.Item()
    ORDER_PASS2 = helper.Item()
    ORDER_AMOUNT = helper.Item()
    ORDER_COMMENT = helper.Item()


class CallbackFuncs:
    ADD_ORDER = 0x00
    ORDER_SHOP = 0x01
    ORDER_HISTORY = 0x02
    ORDER_HISTORY_INFO = 0x03
    SHOP_INFO = 0x04
    FAQ = 0x05
    FAQ_QUESTION = 0x06
    HELP = 0x07
    ORDERS = 0x08


class ReplyKeyboardMarkup(RKM):
    def __bool__(self):
        return bool(self.keyboard)


class InlineKeyboardMarkup(IKM):
    def __bool__(self):
        return bool(self.keyboard)


class ButtonSet(helper.Helper):
    mode = helper.HelperMode.lowercase
    REMOVE = helper.Item()
    START = helper.Item()
    INL_ORDERS = helper.Item()
    INL_ORDER_SHOPS = helper.Item()
    INL_ORDER_HISTORY = helper.Item()
    INL_SHOPS = helper.Item()
    INL_HELP = helper.Item()
    INL_FAQ = helper.Item()
    INL_QUESTION = helper.Item()
    INL_INVOICE = helper.Item()
    INL_ORDER_HISTORY_ORDER = helper.Item()

    def __new__(cls, btn_set: helper.Item = None, args=None, row_width=1):
        if btn_set == cls.REMOVE:
            return ReplyKeyboardRemove()
        key = ReplyKeyboardMarkup(resize_keyboard=True, row_width=row_width)
        ikey = InlineKeyboardMarkup(row_width=row_width)
        if btn_set == cls.START:
            key.row_width = 2
            key.add(*(KeyboardButton(x) for x in (preferences.Texts.btn_profile, preferences.Texts.btn_orders,
                                                  preferences.Texts.btn_shop_list, preferences.Texts.btn_help)))
        elif btn_set == cls.INL_ORDERS:
            ikey.add(*(InlineKeyboardButton(x, callback_data=set_callback(y)) for x, y in (
                (preferences.Texts.btn_add_order, CallbackFuncs.ADD_ORDER),
                (preferences.Texts.btn_order_history, CallbackFuncs.ORDER_HISTORY))))
        elif btn_set == cls.INL_ORDER_SHOPS:
            ikey.add(*(InlineKeyboardButton(x, callback_data=set_callback(CallbackFuncs.ORDER_SHOP, y)) for x, y in args))

        elif btn_set == cls.INL_ORDER_HISTORY:
            ikey.add(*(InlineKeyboardButton(x, callback_data=set_callback(CallbackFuncs.ORDER_HISTORY_INFO, y)) for x, y in args))
            ikey.add(InlineKeyboardButton(preferences.Texts.btn_back, callback_data=set_callback(CallbackFuncs.ORDERS)))
        elif btn_set == cls.INL_ORDER_HISTORY_ORDER:
            ikey.add(InlineKeyboardButton(preferences.Texts.btn_back, callback_data=set_callback(CallbackFuncs.ORDER_HISTORY)))

        elif btn_set == cls.INL_SHOPS:
            ikey.add(*(InlineKeyboardButton(x, callback_data=set_callback(CallbackFuncs.SHOP_INFO, y)) for x, y in args))
        elif btn_set == cls.INL_HELP:
            ikey.add(InlineKeyboardButton(preferences.Texts.btn_faq, callback_data=set_callback(CallbackFuncs.FAQ)))
            ikey.add(InlineKeyboardButton(preferences.Texts.btn_support, url=preferences.Settings.user_support))
        elif btn_set == cls.INL_FAQ:
            ikey.add(*(InlineKeyboardButton(x, callback_data=set_callback(CallbackFuncs.FAQ_QUESTION, y)) for x, y in args))
            ikey.add(InlineKeyboardButton(preferences.Texts.btn_back, callback_data=set_callback(CallbackFuncs.HELP)))
        elif btn_set == cls.INL_QUESTION:
            ikey.add(InlineKeyboardButton(preferences.Texts.btn_back, callback_data=set_callback(CallbackFuncs.FAQ)))
        elif btn_set == cls.INL_INVOICE:
            ikey.add(InlineKeyboardButton(preferences.Texts.btn_invoice, url=args))
        return key or ikey


def answer(message, text, reply_markup=None, pm=True, **kwargs):
    def send_message(func, _type, *types, **kw):
        for t in types:
            if kwargs.get(t):
                del kwargs[t]
        try:
            func(message.chat.id, reply_markup=reply_markup, parse_mode='HTML' if pm else None, **kwargs, **kw)
        except ApiTelegramException:
            del kwargs[_type]
            misc.bot.send_message(message.chat.id, text, parse_mode='HTML' if pm else None, **kwargs, **kw)
    if text == '-':
        text = None
    if kwargs.get('photo') and kwargs['photo'] != '-':
        send_message(misc.bot.send_photo, 'photo', 'data', 'animation', caption=text)
    elif kwargs.get('data') and kwargs['data'] != '-':
        send_message(misc.bot.send_video, 'data', 'photo', 'animation', caption=text)
    elif kwargs.get('animation') and kwargs['animation'] != '-':
        send_message(misc.bot.send_animation, 'animation', 'photo', 'data', caption=text)
    else:
        send_message(misc.bot.send_message, None, 'photo', 'data', 'animation', text=text, disable_web_page_preview=True)


def user_handler(function):
    def decorator(message, **kwargs):
        user, created = models.User.objects.get_or_create(
                                       user_id=message.from_user.id,
                                       defaults={'user_id': message.from_user.id,
                                                 'username': message.from_user.username,
                                                 'first_name': message.from_user.first_name,
                                                 'last_name': message.from_user.last_name})
        if not created:
            if user.is_banned:
                return
            user.username = message.from_user.username
            user.first_name = message.from_user.first_name
            user.last_name = message.from_user.last_name
            user.save()
        kwargs['user'] = user
        # kwargs['created'] = created
        if function.__name__ == 'decorator':
            expected = kwargs
        else:
            expected = {key: kwargs[key] for key in function.__code__.co_varnames if kwargs.get(key) is not None}
        return function(message, **expected)
    return decorator


def logger_middleware(type_, content=None, is_callback=False):
    def wrapper(function):
        def decorator(message, *args, **kwargs):
            user = get_instance(args, models.User)
            if not user:
                user = kwargs.get('user')
            if user:
                button = None
                if is_callback:
                    callback = get_instance(args, CallbackQuery)
                    key = callback.message.reply_markup.to_dict()['inline_keyboard']
                    button = [res[0] for res in [[button['text'] for button in row if button.get('callback_data') == callback.data] for row in key] if res][0]
                models.Log.objects.create(user=user, type=type_, content=content or button or message.text)
            return function(message, *args, **kwargs)
        return decorator
    return wrapper


def reset_state_checker(function):
    def decorator(message, *args, **kwargs):
        user = get_instance(args, models.User)
        if not user:
            user = kwargs.get('user')
        if user and message.text == user.language.btn_back:
            user.reset_state()
            answer(message, preferences.Texts.start_key_message, reply_markup=ButtonSet(ButtonSet.START))
            return
        return function(message, *args, **kwargs)
    return decorator


def get_instance(__objects, __class_or_tuple):
    for __obj in __objects:
        if isinstance(__obj, __class_or_tuple):
            return __obj


def exec_protected(func, *args, **kwargs):
    # noinspection PyBroadException
    try:
        func(*args, **kwargs)
    except Exception:
        for admin in settings.ADMINS_:
            with suppress(Exception):
                misc.bot.send_message(admin, traceback.format_exc())


def set_callback(func, data=None):
    return callback_data.CallbackData('@', 'func', 'json', sep='&').new(func, json.dumps(data, separators=(',', ':')))


def get_callback(data):
    try:
        cd = callback_data.CallbackData('@', 'func', 'json', sep='&').parse(data)
    except ValueError:
        return
    parsed = cd.get('json')
    func = cd.get('func')
    if parsed is None or func is None or not func.isdigit():
        return
    return int(func), json.loads(parsed)


def get_command_args(message):
    text = message.text or message.caption
    command, *args = text.split(maxsplit=1)
    return args[0] if args else ''


def broadcast_to_admins(text, func=misc.bot.send_message, **kwargs):
    if preferences.Settings.admins:
        for admin in preferences.Settings.admins.split():
            with suppress(ApiTelegramException):
                func(admin, text, **kwargs)


def status_emoji(status):
    data = {
        Order.AWAITING: preferences.Texts.order_status_awaiting,
        Order.DECLINED: preferences.Texts.order_status_declined,
        Order.IN_PROGRESS: preferences.Texts.order_status_in_progress,
        Order.FAILED: preferences.Texts.order_status_failed,
        Order.DONE_AWAITING_PAYMENT: preferences.Texts.order_status_done_awaiting_payment,
        Order.PAYED: preferences.Texts.order_status_payed,
    }
    return data.get(status, '-')


def create_invoice(amount, order_id):
    url = "https://api.nowpayments.io/v1/invoice"
    payload = json.dumps({
        "price_amount": float(amount),
        "price_currency": "usd",
        # "pay_currency": "etc",
        "order_id": str(order_id),
        "order_description": f"Order #{order_id}",
        "ipn_callback_url": settings.PAYMENT_URL,
        "success_url": "https://t.me/" + misc.bot.get_me().username,
        "cancel_url": "https://t.me/" + misc.bot.get_me().username
    })
    headers = {
        'x-api-key': preferences.Settings.payment_api_key,
        'Content-Type': 'application/json'
    }
    response = requests.post(url, headers=headers, data=payload)
    return response.json().get('invoice_url')
