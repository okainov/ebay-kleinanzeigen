import os
import re
import sys

import requests
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.background import BackgroundScheduler
from telegram import Update, Message
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

import utils

jobstores = {
    'default': SQLAlchemyJobStore(url='sqlite:///jobs.sqlite')
}
# TODO: re-enable SQLite storage for persistency
#scheduler = BackgroundScheduler(jobstores=jobstores)
scheduler = BackgroundScheduler()
scheduler.start()

last_items = {}

logger = utils.get_logger()


class Item:
    def __init__(self, title, price, torg, url, image):
        self.title = title
        self.price = price
        self.torg = torg
        self.url = 'https://www.ebay-kleinanzeigen.de' + url
        #self.date = date
        self.image = image

    def __repr__(self):
        return f'{self.title} - {self.price}'

    def __str__(self):
        result = f'{self.title} - {self.price}'
        if self.torg:
            result += ' VB'
        #result += f'\n\t{self.date}\n'

        result += self.url
        result += '\n'
        return result


def get_items_per_url(url):
    log = utils.get_logger()
    # Simulate browser headers
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36',
        'Host': 'www.ebay-kleinanzeigen.de',
        'Accept': '*/*',
        }

    qq = requests.get(url, headers=headers)

    text = qq.text

    articles = re.findall('<article(.*?)</article', text, re.S)
    log.info('Articles length %s' % len(articles))
    items = []
    for item in articles:
        if results := re.findall('<a.*?href="(.*?)">(.*?)</a>', item, re.S):
            url, name = results[0]

        else:
            continue

        price_line = re.findall('aditem-main--middle--price">(.*?)</p>', item, re.S)
        if len(price_line) > 0:
            price_line = price_line[0]
        else:
            price_line = 0
        torg = 'VB' in price_line
        price = None
        if prices := re.findall(r'\d+', price_line, re.S):
            price = int(prices[0])

        # date = re.findall('aditem-addon">(.*?)</', item, re.S)[0].strip()
        # if '{' in date or '<' in date:
        #     continue

        try:
            image = re.findall('imgsrc="(.*?)"', item, re.S)[0].strip()
        except Exception as e:
            logger.error(f'No image\n\t{item}')
            continue
        log.info("image: " + image)
        log.info("URL " + url)
        log.info("Title " + name)
        log.info("Price " + price)
        items.append(Item(name, price, torg, url, image))
    return items


def start(update, context):
    """Send a message when the command /start is issued."""
    log = utils.get_logger()
    log.info('Start')
    update.message.reply_text('Hi!')


def error(update, context):
    """Log Errors caused by Updates."""
    print('Update "%s" caused error "%s"', update, context.error)


def echo(update: Update, context):
    msg: Message = update.message

    url = update.message.text
    chat_id = update.effective_chat.id

    log = utils.get_logger()
    log.info('Started echo')

    if chat_id not in last_items:
        # Nothing here, schedule
        scheduler.add_job(echo, trigger='interval', args=(update, context), minutes=2, id=str(chat_id))
        log.info('Scheduled job')
        last_items[chat_id] = {'last_item': None, 'url': url}

    log.info("Get items")
    items = get_items_per_url(url)
    for item in items:
        if chat_id in last_items and item.url == last_items[chat_id]['last_item']:
            #log.info('Breaking the loop')
            break
        msg.reply_text(str(item))
        # update.message.reply_photo(item.image)
    last_items[chat_id] = {'last_item': items[0].url, 'search_url': url}


def main():
    """Start the bot."""
    # Create the Updater and pass it your bot's token.
    # Make sure to set use_context=True to use the new context based callbacks
    # Post version 12 this will no longer be necessary

    updater = Updater(bot=utils.get_bot(), use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text, echo))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    DEBUG = True if os.getenv("DEBUG") else False
    BOT_TOKEN = os.getenv("TG_TOKEN")
    if DEBUG:
        updater.start_polling()
        # Run the bot until you press Ctrl-C or the process receives SIGINT,
        # SIGTERM or SIGABRT. This should be used most of the time, since
        # start_polling() is non-blocking and will stop the bot gracefully.
        updater.idle()
    else:
        logger.info('Starting bot in production webhook mode')
        HOST_URL = os.environ.get("HOST_URL")
        if HOST_URL is None:
            logger.critical('HOST URL is not set!')
            sys.exit(-1)
        updater.start_webhook(listen="0.0.0.0",
                              port='8443',
                              url_path=BOT_TOKEN)
        updater.bot.set_webhook("https://{}/{}".format(HOST_URL, BOT_TOKEN))


if __name__ == '__main__':
    main()
