from os import environ
from time import sleep
from contextlib import suppress
from django import setup
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton


def send_post(post, user):
    key = None
    if post.button and post.link:
        key = InlineKeyboardMarkup()
        key.add(InlineKeyboardButton(text=post.button, url=post.link))
    if post.photo_id:
        bot.send_photo(user, photo=post.photo_id, caption=post.message, parse_mode='HTML', reply_markup=key)
    elif post.gif_id:
        bot.send_animation(user, animation=post.gif_id, caption=post.message, parse_mode='HTML', reply_markup=key)
    else:
        bot.send_message(user, text=post.message, parse_mode='HTML', disable_web_page_preview=not post.preview, reply_markup=key)


def process_post(post):
    if not post:
        return
    post.refresh_from_db()
    post.status = Post.SEND
    post.save()

    users = models.User.objects.order_by('-created')
    users = [user.user_id for user in users]

    receivers = 0
    for user in users:
        with suppress(Exception):
            send_post(post, user)
            receivers += 1
        sleep(.05)

    post.refresh_from_db()
    post.status = Post.DONE
    post.receivers = receivers
    post.save()


def main():
    while True:
        with suppress(Exception):
            for post in models.Post.objects.filter(status=Post.WAIT).order_by('created'):
                process_post(post)
        sleep(5)


if __name__ == '__main__':
    import sys
    sys.path.append('.')
    environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
    setup()
    from bot import models
    from bot.misc import bot
    from bot.types import Post
    main()
