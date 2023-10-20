from contextlib import suppress
from django.contrib import admin
from django.utils.html import format_html
from django.contrib.auth.models import User as DjangoUser, Group as DjangoGroup
from preferences.admin import PreferencesAdmin
from preferences import preferences

from bot import models, types, utils, misc

admin.site.site_header = admin.site.site_title = 'Bot administration'
admin.site.site_url = ''

admin.site.unregister(DjangoUser)
admin.site.unregister(DjangoGroup)
admin.site.enable_nav_sidebar = False


class UserAdmin(admin.ModelAdmin):
    list_display = ['created', 'user_id', 'username_custom', 'first_name', 'last_name', 'service_fee', 'is_banned']
    list_editable = ['is_banned', 'service_fee']
    list_filter = ['is_banned']
    list_display_links = None
    search_fields = ['user_id', 'username', 'first_name', 'last_name']
    date_hierarchy = 'created'

    def username_custom(self, obj):
        if obj.username:
            return format_html(f'<a href="tg://resolve?domain={obj.username}">@{obj.username}</a>')
        else:
            return '-'
    username_custom.short_description = '@username'

    def has_add_permission(self, *args, **kwargs):
        return False

    def has_change_permission(self, *args, **kwargs):
        return True

    def has_delete_permission(self, *args, **kwargs):
        return False


class LogAdmin(admin.ModelAdmin):
    list_display = ['created', 'user_custom', 'type', 'content']
    list_display_links = None

    date_hierarchy = 'created'
    search_fields = ['user__user_id']
    list_filter = ['type']

    def user_custom(self, obj):
        if obj.user:
            return format_html(f'<a href="/bot/user/?q={obj.user.user_id}">{obj.user.user_id}</a>')
        else:
            return '-'
    user_custom.short_description = 'User ID'

    def has_add_permission(self, *args, **kwargs):
        return False

    def has_change_permission(self, *args, **kwargs):
        return False

    def has_delete_permission(self, *args, **kwargs):
        return False


class OrderAdmin(admin.ModelAdmin):
    list_display = ['created', 'user_custom', 'log', 'pass1', 'shop', 'pass2', 'amount', 'comment', 'status']
    list_display_links = None

    date_hierarchy = 'created'
    search_fields = ['user__user_id', 'shop__name']
    list_filter = ['status']
    list_editable = ['status']

    fieldsets = [('Information', {'fields': ['created', 'user_custom', 'log', 'pass1', 'shop', 'pass2', 'amount', 'comment', 'status']})]
    readonly_fields = ['created', 'user_custom', 'log', 'pass1', 'shop', 'pass2', 'amount', 'comment']

    def save_model(self, request, obj, form, change):
        super(OrderAdmin, self).save_model(request, obj, form, change)
        if obj.status == types.Order.DONE_AWAITING_PAYMENT:
            invoice_url = utils.create_invoice(obj.amount * (obj.user.service_fee if obj.user.service_fee is not None else preferences.Settings.service_fee) / 100, obj.id)
            with suppress(Exception):
                misc.bot.send_message(obj.user.user_id, preferences.Texts.order_invoice,
                                      reply_markup=utils.ButtonSet(utils.ButtonSet.INL_INVOICE, invoice_url), parse_mode='HTML')

    def user_custom(self, obj):
        if obj.user:
            return format_html(f'<a href="/bot/user/?q={obj.user.user_id}">{obj.user.user_id}</a>')
        else:
            return '-'
    user_custom.short_description = 'User ID'

    def has_add_permission(self, *args, **kwargs):
        return False

    def has_change_permission(self, *args, **kwargs):
        return True

    def has_delete_permission(self, *args, **kwargs):
        return False


class PaymentAdmin(admin.ModelAdmin):
    list_display = ['created', 'user_custom', 'amount']
    list_display_links = None

    date_hierarchy = 'created'
    search_fields = ['user__user_id']

    def user_custom(self, obj):
        if obj.user:
            return format_html(f'<a href="/bot/user/?q={obj.user.user_id}">{obj.user.user_id}</a>')
        else:
            return '-'
    user_custom.short_description = 'User ID'

    def has_add_permission(self, *args, **kwargs):
        return False

    def has_change_permission(self, *args, **kwargs):
        return False

    def has_delete_permission(self, *args, **kwargs):
        return False


class CountryAdmin(admin.ModelAdmin):
    list_display = ['name', 'shops']
    list_display_links = None
    list_editable = ['name']
    search_fields = ['name']

    fieldsets = [
        ('Parameters', {'fields': ['name']})
    ]

    def shops(self, obj):
        return models.Shop.objects.filter(country=obj).count()
    shops.short_description = 'Shops count'

    def has_add_permission(self, *args, **kwargs):
        return True

    def has_change_permission(self, *args, **kwargs):
        return True

    def has_delete_permission(self, *args, **kwargs):
        return True


class ShopAdmin(admin.ModelAdmin):
    list_display = ['name', 'country', 'limit', 'quantity', 'timeframe', 'pass2', 'comment', 'available']
    list_display_links = ['name']
    list_editable = ['available']
    search_fields = ['name']

    fieldsets = [
        ('Parameters', {'fields': list_display})
    ]

    def has_add_permission(self, *args, **kwargs):
        return True

    def has_change_permission(self, *args, **kwargs):
        return True

    def has_delete_permission(self, *args, **kwargs):
        return True


class QuestionAdmin(admin.ModelAdmin):
    list_display = ['title', 'answer']
    list_display_links = None
    list_editable = ['title', 'answer']
    search_fields = ['title']

    fieldsets = [
        ('Parameters', {'fields': list_display})
    ]

    def has_add_permission(self, *args, **kwargs):
        return True

    def has_change_permission(self, *args, **kwargs):
        return True

    def has_delete_permission(self, *args, **kwargs):
        return True


class SettingsAdmin(PreferencesAdmin):
    change_form_template = 'admin/settings_form.html'

    fieldsets = [
        ('Parameters', {'fields': ['service_fee', 'payment_api_key', 'user_support', 'admins']}),
    ]

    def change_view(self, *args, **kwargs):
        if not kwargs.get('extra_context'):
            kwargs['extra_context'] = {}
        kwargs['extra_context']['show_save_and_continue'] = False
        return super().change_view(*args, **kwargs)

    def has_add_permission(self, *args, **kwargs):
        return False

    def has_change_permission(self, *args, **kwargs):
        return True

    def has_delete_permission(self, request, obj=None):
        return False


class TextsAdmin(PreferencesAdmin):
    change_form_template = 'admin/text_change_form.html'

    fieldsets = [
        ('Texts', {'fields': [
                'start_message',
                'profile',
                'orders',
                'shop_list',
                'help',
                'faq',
                # 'support',
                'order_log',
                'order_pass',
                'order_shop',
                'order_pass2',
                'order_amount',
                'order_comment',
                'order_invoice',
                'order_created',
                'order_history',
                'order_full_info',
                'shop_full_info',
                'order_status_awaiting',
                'order_status_declined',
                'order_status_in_progress',
                'order_status_failed',
                'order_status_done_awaiting_payment',
                'order_status_payed',
                'wrong_format',
                'unknown_action',
            ]}),
        ('Buttons', {'fields': [
                'btn_profile',
                'btn_orders',
                'btn_shop_list',
                'btn_help',
                'btn_add_order',
                'btn_order_history',
                'btn_history_line',
                'btn_invoice',
                'btn_faq',
                'btn_support',
                'btn_back',
            ]}),
    ]

    def change_view(self, *args, **kwargs):
        if not kwargs.get('extra_context'):
            kwargs['extra_context'] = {}
        kwargs['extra_context']['show_save_and_continue'] = False
        return super().change_view(*args, **kwargs)

    def has_add_permission(self, *args, **kwargs):
        return False

    def has_change_permission(self, *args, **kwargs):
        return True

    def has_delete_permission(self, request, obj=None):
        return False


class PostAdmin(admin.ModelAdmin):
    change_form_template = 'admin/text_change_form.html'

    list_display = ['created', 'status', 'receivers_custom', 'media_custom', 'text_custom', 'keyboard_custom']

    fieldsets = [
        ('Media', {'fields': ['photo_id', 'gif_id']}),
        ('Text', {'fields': ['message', 'preview']}),
        ('Keyboard', {'fields': ['button', 'link']}),
    ]

    date_hierarchy = 'created'
    search_fields = ['photo_id', 'gif_id', 'message', 'button', 'link']
    list_filter = ['status']
    list_per_page = 10

    def receivers_custom(self, obj):
        if obj.receivers is not None:
            return format_html(f'<b>{obj.receivers}</b>')
        else:
            return '-'
    receivers_custom.short_description = 'Receivers'

    def media_custom(self, obj):
        file_id = obj.photo_id or obj.gif_id
        return file_id or '-'
    media_custom.short_description = 'Media'

    def text_custom(self, obj):
        text = obj.message.replace('\n', '<br>')
        if obj.preview:
            text += '<br><br>(preview)'
        return format_html(text)
    text_custom.short_description = 'Text'

    def keyboard_custom(self, obj):
        if obj.button and obj.link:
            return format_html(f'<a href="{obj.link}" target="_blank">{obj.button}</a>')
        else:
            return '-'
    keyboard_custom.short_description = 'Button'

    def change_view(self, *args, **kwargs):
        if not kwargs.get('extra_context'):
            kwargs['extra_context'] = {}
        kwargs['extra_context']['show_save_and_continue'] = False
        return super().change_view(*args, **kwargs)

    def has_change_permission(self, request, obj=None):
        return (obj is None) or (obj.status in [types.Post.WAIT])

    def has_delete_permission(self, request, obj=None):
        return (obj is None) or (obj.status in [types.Post.WAIT, types.Post.DONE])


admin.site.register(models.User, UserAdmin)
admin.site.register(models.Log, LogAdmin)
admin.site.register(models.Order, OrderAdmin)
admin.site.register(models.Payment, PaymentAdmin)
admin.site.register(models.Country, CountryAdmin)
admin.site.register(models.Shop, ShopAdmin)
admin.site.register(models.Question, QuestionAdmin)
admin.site.register(models.Settings, SettingsAdmin)
admin.site.register(models.Texts, TextsAdmin)
admin.site.register(models.Post, PostAdmin)
