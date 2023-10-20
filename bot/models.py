import json
from django.db import models
from preferences.models import Preferences
from bot import types


class User(models.Model):
    created = models.DateTimeField('🕐 Created, UTC', auto_now_add=True)
    user_id = models.BigIntegerField('ID', unique=True, primary_key=True)
    username = models.CharField('@username', max_length=256, blank=True, null=True)
    first_name = models.CharField('First name', max_length=256, blank=True, null=True)
    last_name = models.CharField('Last name', max_length=256, blank=True, null=True)
    service_fee = models.DecimalField('Service fee', max_digits=10, decimal_places=3, blank=True, null=True)
    is_banned = models.BooleanField('Ban', default=False)
    # service only
    state = models.CharField(max_length=256, default=None, null=True)
    state_data = models.TextField(max_length=16384, default=None, null=True)

    def set_state(self, state):
        self.state = state
        self.save()

    def reset_state(self):
        self.state = None
        self.state_data = None
        self.save()

    def get_state_data(self) -> dict:
        return json.loads(self.state_data or '{}')

    def update_state_data(self, data: dict) -> dict:
        temp = json.loads(self.state_data or '{}')
        temp.update(data)
        self.state_data = json.dumps(temp)
        self.save()
        return temp

    def __str__(self):
        return str(self.user_id)

    class Meta:
        ordering = ('-created',)
        verbose_name = 'user'
        verbose_name_plural = 'users'


class Log(models.Model):
    TYPES = ((types.Log.TEXT, '🅰️ Text'), (types.Log.REPLY_BUTTON, '⏹ Reply-button'),
             (types.Log.INLINE_BUTTON, '⏺ Inline-button'), (types.Log.COMMAND, '✳️ Command'))
    created = models.DateTimeField('🕐 Created, UTC', auto_now_add=True)
    user = models.ForeignKey(User, models.CASCADE)
    type = models.CharField('Type', max_length=16, choices=TYPES)
    content = models.CharField('Content', max_length=4096, blank=True, null=True)

    def __str__(self):
        return str(self.content)

    class Meta:
        ordering = ('-created',)
        verbose_name = 'log'
        verbose_name_plural = 'logs'


class Country(models.Model):
    name = models.CharField('Name', max_length=128)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'country'
        verbose_name_plural = 'countries'


class Shop(models.Model):
    name = models.CharField('Name', max_length=128)
    country = models.ForeignKey(Country, models.CASCADE)
    limit = models.PositiveIntegerField('Limit')
    quantity = models.PositiveIntegerField('Qty')
    timeframe = models.CharField('Timeframe', max_length=128)
    pass2 = models.BooleanField('Pass2')
    comment = models.CharField('Comment', max_length=4096)
    available = models.BooleanField('Available', default=True)

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = 'shop'
        verbose_name_plural = 'shops'


class Order(models.Model):
    STATUSES = ((types.Order.AWAITING, '⏱ Awaiting'), (types.Order.DECLINED, '❌ Declined'),
                (types.Order.IN_PROGRESS, '⏳ In progress'), (types.Order.FAILED, '⛔️ Failed'),
                (types.Order.DONE_AWAITING_PAYMENT, '💳 Done, awaiting for payment'), (types.Order.PAYED, '✅ Payed'))
    created = models.DateTimeField('🕐 Created, UTC', auto_now_add=True)
    user = models.ForeignKey(User, models.CASCADE)
    log = models.CharField('Log', max_length=4096)
    pass1 = models.CharField('Pass', max_length=4096)
    shop = models.ForeignKey(Shop, models.CASCADE)
    pass2 = models.CharField('Pass2', max_length=4096, default=None, null=True)
    amount = models.PositiveIntegerField('Amount')
    comment = models.CharField('Comment', max_length=4096)
    status = models.CharField('Status', max_length=32, choices=STATUSES, default=types.Order.AWAITING)

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = 'order'
        verbose_name_plural = 'orders'


class Payment(models.Model):
    created = models.DateTimeField('🕐 Created, UTC', auto_now_add=True)
    user = models.ForeignKey(User, models.CASCADE)
    amount = models.DecimalField('Amount, $', max_digits=10, decimal_places=2)

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = 'payment'
        verbose_name_plural = 'payments'


class Question(models.Model):
    title = models.CharField('Title', max_length=128)
    answer = models.TextField('Answer', max_length=4096)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = 'question'
        verbose_name_plural = 'questions'


class Settings(Preferences):
    change_form_template = 'admin/settings_form.html'

    service_fee = models.DecimalField('Service fee', max_digits=10, decimal_places=3, default=1.0)
    payment_api_key = models.CharField('Nowpayments API key', max_length=128, default='-')
    user_support = models.CharField('Support user link', max_length=64, blank=True, default=None, null=True)
    admins = models.TextField('Admins list, ID', max_length=128, blank=True, default=None, null=True)
    admins.help_text = "Admins receive notifications about new orders.<br>" \
                       "Several admins are specified with a space or a line break."

    def __str__(self):
        return 'Settings'

    class Meta:
        verbose_name = 'list'
        verbose_name_plural = 'lists'


class Texts(Preferences):
    change_form_template = 'admin/text_change_form.html'

    start_message = types.Message('Welcome message')
    profile = types.Message('Profile')
    orders = types.Message('Orders')
    shop_list = types.Message('Shop list')
    help = types.Message('Help')
    faq = types.Message('Faq')
    support = types.Message('Customer support')
    order_log = types.Message('Order • Log')
    order_pass = types.Message('Order • Pass')
    order_shop = types.Message('Order • Shop')
    order_pass2 = types.Message('Order • Pass2')
    order_amount = types.Message('Order • Amount')
    order_comment = types.Message('Order • Comment')
    order_invoice = types.Message('Order • Invoice')
    order_created = types.Message('Order • Created')
    order_history = types.Message('Order • History')
    order_full_info = types.Message('Order • Full info')
    shop_full_info = types.Message('Shop • Full info')
    order_status_awaiting = models.CharField('Order status • Awaiting', max_length=32, default='-')
    order_status_declined = models.CharField('Order status • Declined', max_length=32, default='-')
    order_status_in_progress = models.CharField('Order status • In progress', max_length=32, default='-')
    order_status_failed = models.CharField('Order status • Failed', max_length=32, default='-')
    order_status_done_awaiting_payment = models.CharField('Order status • Done, awaiting payment', max_length=32, default='-')
    order_status_payed = models.CharField('Order status • Payed', max_length=32, default='-')
    wrong_format = types.Message('Wrong format')
    unknown_action = types.Message('Unknown action')

    btn_profile = types.Button('⏹ Profile')
    btn_orders = types.Button('⏹ Orders')
    btn_shop_list = types.Button('⏹ Shop list')
    btn_help = types.Button('⏹ Help')
    btn_add_order = types.Button('⏹ Add order')
    btn_order_history = types.Button('⏹ Order history')
    btn_history_line = types.Button('⏹ History info')
    btn_invoice = types.Button('⏹ Order invoice')
    btn_faq = types.Button('⏹ FAQ')
    btn_support = types.Button('⏹ Customer support')
    btn_back = types.Button('⏹ Back')

    def __str__(self):
        return 'Texts'

    class Meta:
        verbose_name = 'list'
        verbose_name_plural = 'lists'


class Post(models.Model):
    STATUSES = ((types.Post.WAIT, '⏳ Awaiting'), (types.Post.SEND, '📨 Sending'), (types.Post.DONE, '🎫 Done'))
    created = models.DateTimeField('🕐 Created, UTC', auto_now_add=True)
    status = models.CharField('Status', max_length=4, choices=STATUSES, default=types.Post.WAIT)
    photo_id = models.CharField('Photo', max_length=128, blank=True, null=True)
    photo_id.help_text = "Specified by FileID, you can get it by sending the photo you need to the bot."
    gif_id = models.CharField('GIF', max_length=128, blank=True, null=True)
    gif_id.help_text = "Specified by FileID, you can get it by sending the gif you need to the bot."
    message = models.TextField("Message", max_length=1024)
    preview = models.BooleanField("Preview", default=False)
    button = models.CharField("Button", max_length=256, blank=True, null=True)
    link = models.URLField("Link", blank=True, null=True)
    receivers = models.IntegerField("Receivers", blank=True, null=True)

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = 'post'
        verbose_name_plural = 'posts'
