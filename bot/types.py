from bot.utils_lib import helper
from django.db import models


class Log(helper.HelperMode):
    mode = helper.HelperMode.SCREAMING_SNAKE_CASE
    TEXT = helper.Item()
    REPLY_BUTTON = helper.Item()
    INLINE_BUTTON = helper.Item()
    COMMAND = helper.Item()


class Order(helper.HelperMode):
    mode = helper.HelperMode.SCREAMING_SNAKE_CASE
    AWAITING = helper.Item()
    DECLINED = helper.Item()
    IN_PROGRESS = helper.Item()
    FAILED = helper.Item()
    DONE_AWAITING_PAYMENT = helper.Item()
    PAYED = helper.Item()


class Post(helper.HelperMode):
    WAIT = helper.Item()
    SEND = helper.Item()
    DONE = helper.Item()


class Message(models.TextField):
    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 4096
        kwargs['default'] = '-'
        super().__init__(*args, **kwargs)


class Button(models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 64
        kwargs['default'] = '-'
        super().__init__(*args, **kwargs)


class Media(models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 128
        kwargs['default'] = '-'
        super().__init__(*args, **kwargs)


class Alert(models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 200
        kwargs['default'] = '-'
        super().__init__(*args, **kwargs)
