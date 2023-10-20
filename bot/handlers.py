from preferences import preferences
from telebot import types
from bot import models, utils
from bot.misc import bot
from bot.utils import answer, ButtonSet
from bot.types import Log


# noinspection PyUnusedLocal
@bot.message_handler(commands=['start'])
@utils.user_handler
@utils.logger_middleware(Log.COMMAND)
def start_handler(message: types.Message, user: models.User):
    user.reset_state()
    answer(message, preferences.Texts.start_message, reply_markup=ButtonSet(ButtonSet.START))


@bot.message_handler(content_types=['text'])
@utils.user_handler
def distribute_state_text_handler(message: types.Message, user: models.User):
    if main_text_handler(message, user):
        return
    state_funcs = {
        utils.States.ORDER_LOG: order_log,
        utils.States.ORDER_PASS: order_pass1,
        utils.States.ORDER_SHOP: order_shop,
        utils.States.ORDER_PASS2: order_pass2,
        utils.States.ORDER_AMOUNT: order_amount,
        utils.States.ORDER_COMMENT: order_comment,
    }
    if state_funcs.get(user.state):
        state_funcs[user.state](message, user)
    else:
        else_text_handler(message, user)


@bot.message_handler(content_types=['photo', 'animation', 'video'])
def media_handler(message: types.Message):
    if message.photo:
        answer(message, f'<code>{message.photo[-1].file_id}</code>')
    elif message.animation:
        answer(message, f'<code>{message.animation.file_id}</code>')
    elif message.video:
        answer(message, f'<code>{message.video.file_id}</code>')


@bot.callback_query_handler(lambda callback: True)
@utils.user_handler
def callback_handler(callback: types.CallbackQuery, user: models.User):
    data = utils.get_callback(callback.data)
    if data is None:
        return
    func, data = data
    callback_funcs = {
        utils.CallbackFuncs.ADD_ORDER: add_order_chain_start,
        utils.CallbackFuncs.ORDER_SHOP: order_shop,
        utils.CallbackFuncs.ORDER_HISTORY: orders_history,
        utils.CallbackFuncs.ORDER_HISTORY_INFO: order_info,
        utils.CallbackFuncs.SHOP_INFO: shop_info,
        utils.CallbackFuncs.FAQ: send_faq,
        utils.CallbackFuncs.FAQ_QUESTION: send_faq_answer,
        utils.CallbackFuncs.HELP: send_help_inline,
        utils.CallbackFuncs.ORDERS: orders_inline,
    }
    if callback_funcs.get(func):
        callback_funcs[func](callback.message, callback, user, data)


def main_text_handler(message: types.Message, user):
    if message.text == preferences.Texts.btn_profile:
        send_profile(message, user)
    elif message.text == preferences.Texts.btn_orders:
        send_orders(message, user)
    elif message.text == preferences.Texts.btn_shop_list:
        send_shop_list(message, user)
    elif message.text == preferences.Texts.btn_help:
        send_help(message, user)
    else:
        return False
    return True


@utils.logger_middleware(Log.TEXT)
def else_text_handler(message, user):
    user.reset_state()
    answer(message, preferences.Texts.unknown_action, reply_markup=ButtonSet(ButtonSet.START))


@utils.logger_middleware(Log.REPLY_BUTTON)
def send_profile(message: types.Message, user):
    orders = models.Order.objects.filter(user=user)
    answer(message, preferences.Texts.profile.format(first_launch=user.created.strftime("%d.%m.%Y %H:%M"), orders_qty=orders.count(),
                                                     total=sum(x.amount for x in orders), fee=user.service_fee if user.service_fee is not None else preferences.Settings.service_fee))


# noinspection PyUnusedLocal
@utils.logger_middleware(Log.REPLY_BUTTON)
def send_orders(message: types.Message, user):
    answer(message, preferences.Texts.orders, reply_markup=ButtonSet(ButtonSet.INL_ORDERS))


@utils.logger_middleware(Log.INLINE_BUTTON, is_callback=True)
def orders_inline(message, callback: types.CallbackQuery, user, data):
    bot.edit_message_text(preferences.Texts.orders, message.chat.id, message.message_id, parse_mode='HTML',
                  reply_markup=ButtonSet(ButtonSet.INL_ORDERS))
    bot.answer_callback_query(callback.id)


# noinspection PyUnusedLocal
@utils.logger_middleware(Log.REPLY_BUTTON)
def send_shop_list(message: types.Message, user):
    buttons = [(x.name, x.id) for x in models.Shop.objects.filter(available=True)]
    answer(message, preferences.Texts.shop_list, reply_markup=ButtonSet(ButtonSet.INL_SHOPS, buttons))


# noinspection PyUnusedLocal
@utils.logger_middleware(Log.REPLY_BUTTON)
def send_help(message: types.Message, user):
    answer(message, preferences.Texts.help, reply_markup=ButtonSet(ButtonSet.INL_HELP))


@utils.logger_middleware(Log.TEXT)
def order_log(message: types.Message, user):
    user.update_state_data({'log': message.text})
    user.set_state(utils.States.ORDER_PASS)
    answer(message, preferences.Texts.order_pass)


@utils.logger_middleware(Log.TEXT)
def order_pass1(message: types.Message, user):
    user.update_state_data({'pass1': message.text})
    user.set_state(utils.States.ORDER_SHOP)
    buttons = [(x.name, x.id) for x in models.Shop.objects.filter(available=True)]
    answer(message, preferences.Texts.order_shop, ButtonSet(ButtonSet.INL_ORDER_SHOPS, buttons))


@utils.logger_middleware(Log.TEXT)
def order_pass2(message: types.Message, user):
    user.update_state_data({'pass2': message.text})
    user.set_state(utils.States.ORDER_AMOUNT)
    answer(message, preferences.Texts.order_amount)


@utils.logger_middleware(Log.TEXT)
def order_amount(message: types.Message, user):
    if not message.text.isdigit():
        answer(message, preferences.Texts.wrong_format)
        return
    user.update_state_data({'amount': int(message.text)})
    user.set_state(utils.States.ORDER_COMMENT)
    answer(message, preferences.Texts.order_comment)


@utils.logger_middleware(Log.TEXT)
def order_comment(message: types.Message, user):
    data = user.update_state_data({'comment': message.text})
    user.reset_state()
    order = models.Order.objects.create(user=user, log=data['log'], pass1=data['pass1'], shop_id=data['shop_id'],
                                        pass2=data.get('pass2'), amount=data['amount'], comment=data['comment'])
    utils.broadcast_to_admins(f'New order: https:///bot/order/{order.id}')
    answer(message, preferences.Texts.order_created, reply_markup=ButtonSet(ButtonSet.START))


# noinspection PyUnusedLocal
@utils.logger_middleware(Log.INLINE_BUTTON, is_callback=True)
def add_order_chain_start(message, callback: types.CallbackQuery, user, data):
    # bot.delete_message(message.chat.id, message.message_id)
    user.set_state(utils.States.ORDER_LOG)
    answer(message, preferences.Texts.order_log)
    bot.answer_callback_query(callback.id)


# noinspection PyUnusedLocal
@utils.logger_middleware(Log.INLINE_BUTTON, is_callback=True)
def order_shop(message, callback: types.CallbackQuery, user, data):
    try:
        shop = models.Shop.objects.get(id=data)
    except models.Shop.DoesNotExist:
        return
    user.update_state_data({'shop_id': data})
    bot.answer_callback_query(callback.id)
    if shop.pass2:
        user.set_state(utils.States.ORDER_PASS2)
        answer(message, preferences.Texts.order_pass2)
    else:
        user.set_state(utils.States.ORDER_AMOUNT)
        answer(message, preferences.Texts.order_amount)


# noinspection PyUnusedLocal
@utils.logger_middleware(Log.INLINE_BUTTON, is_callback=True)
def orders_history(message, callback: types.CallbackQuery, user, data):
    bot.answer_callback_query(callback.id)
    buttons = [(preferences.Texts.btn_history_line.format(date=x.created.strftime("%d.%m.%y"), log=x.log, shop=x.shop.name,
                                                          amount=x.amount, status=utils.status_emoji(x.status)), x.id)
               for x in models.Order.objects.filter(user=user).order_by('-created')]
    # answer(message, preferences.Texts.order_history, reply_markup=ButtonSet(ButtonSet.INL_ORDER_HISTORY, buttons))
    bot.edit_message_text(preferences.Texts.order_history, message.chat.id, message.message_id, parse_mode='HTML',
                      reply_markup=ButtonSet(ButtonSet.INL_ORDER_HISTORY, buttons))


# noinspection PyUnusedLocal
@utils.logger_middleware(Log.INLINE_BUTTON, is_callback=True)
def order_info(message, callback: types.CallbackQuery, user, data):
    try:
        order = models.Order.objects.get(id=data)
    except models.Order.DoesNotExist:
        return
    bot.answer_callback_query(callback.id)
    # answer(message, preferences.Texts.order_full_info.format(date=order.created.strftime("%d.%m.%Y %H:%M"), log=order.log, shop=order.shop.name,
    #                                                          amount=order.amount, status=utils.status_emoji(order.status), pass1=order.pass1,
    #                                                          pass2=order.pass2 or '-', comment=order.comment))
    bot.edit_message_text(
        preferences.Texts.order_full_info.format(
            date=order.created.strftime("%d.%m.%Y %H:%M"), log=order.log, shop=order.shop.name,
            amount=order.amount, status=utils.status_emoji(order.status), pass1=order.pass1,
            pass2=order.pass2 or '-', comment=order.comment
        ),
        message.chat.id, message.message_id, parse_mode='HTML',
        reply_markup=ButtonSet(ButtonSet.INL_ORDER_HISTORY_ORDER)
    )


# noinspection PyUnusedLocal
@utils.logger_middleware(Log.INLINE_BUTTON, is_callback=True)
def shop_info(message, callback: types.CallbackQuery, user, data):
    try:
        shop = models.Shop.objects.get(id=data)
    except models.Shop.DoesNotExist:
        return
    bot.answer_callback_query(callback.id)
    answer(message, preferences.Texts.shop_full_info.format(store=shop.name, country=shop.country.name, limit=shop.limit, qty=shop.quantity, timeframe=shop.timeframe, comment=shop.comment))


# noinspection PyUnusedLocal
@utils.logger_middleware(Log.INLINE_BUTTON, is_callback=True)
def send_help_inline(message, callback: types.CallbackQuery, user, data):
    bot.edit_message_text(preferences.Texts.help, message.chat.id, message.message_id, parse_mode='HTML',
                          reply_markup=ButtonSet(ButtonSet.INL_HELP))
    bot.answer_callback_query(callback.id)


# noinspection PyUnusedLocal
@utils.logger_middleware(Log.INLINE_BUTTON, is_callback=True)
def send_faq(message, callback: types.CallbackQuery, user, data):
    buttons = [(x.title, x.id) for x in models.Question.objects.all()]
    bot.edit_message_text(preferences.Texts.faq, message.chat.id, message.message_id, parse_mode='HTML',
                          reply_markup=ButtonSet(ButtonSet.INL_FAQ, buttons))
    bot.answer_callback_query(callback.id)


# noinspection PyUnusedLocal
@utils.logger_middleware(Log.INLINE_BUTTON, is_callback=True)
def send_faq_answer(message, callback: types.CallbackQuery, user, data):
    try:
        q = models.Question.objects.get(id=data)
    except models.Question.DoesNotExist:
        return
    bot.edit_message_text(q.answer, message.chat.id, message.message_id, parse_mode='HTML',
                          reply_markup=ButtonSet(ButtonSet.INL_QUESTION))
    bot.answer_callback_query(callback.id)
