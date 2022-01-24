import logging
from logging.handlers import RotatingFileHandler
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from apscheduler.schedulers.background import BackgroundScheduler
from forismatic import *
from PIL import Image, ImageDraw, ImageFont
import textwrap
from dotenv import dotenv_values
from pymongo import MongoClient
from random import choice, randint
from datetime import date, datetime, timedelta
import pytz
import matplotlib.pyplot as plt
import matplotlib.dates as dates
import numpy as np
import re
import requests
from scipy.interpolate import make_interp_spline
from operator import itemgetter

# https://youtrack.jetbrains.com/issue/PY-39762
# noinspection PyArgumentList
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] %(message)s',
                    handlers=[
                        logging.handlers.RotatingFileHandler('bot.log', maxBytes=100000, backupCount=5),
                        logging.StreamHandler()
                    ])

config = dotenv_values("conf.env")
bot_token = config['bot_token']  # prostavushka_bot
db_login_password = config['db_login_password']
kolya_superdry_allowed_user_id = config['kolya_superdry_allowed_user_id']
home_dir = config['home_dir']

updater = Updater(token=bot_token, use_context=True)  # запуск экземпляра бота


def start(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="I'm ProstavushkaBot, supported commands:"
                                                                    "/dima - Time since @usebooz started his project")


def dima(update, context):
    start = datetime.fromtimestamp(1615969080)
    end = datetime.now()
    elapsed = end - start
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text="Time since @usebooz started his project: %02d days %02d hours %02d minutes "
                                  "%02d seconds" % (
                                      elapsed.days, elapsed.seconds // 3600, elapsed.seconds // 60 % 60,
                                      elapsed.seconds % 60))


def mail(update, context):
    try:
        resp = requests.get(
            "https://eodhistoricaldata.com/api/real-time/VKCO.MCX?api_token=60f7ee9a697e04.95301398&fmt=json").json()
        bid = float(resp["close"])
        regular_market_previous_close = float(resp["previousClose"])
        if bid != 0:
            message = "Цена: %02d ₽\nПредыдущее закрытие: %02d ₽\n" % (
                bid, regular_market_previous_close)
            percent = ((bid - regular_market_previous_close) / regular_market_previous_close) * 100
            if percent > 0:
                message += "Растем 📈 +%.2f %%" % percent
            else:
                message += "Отрицательно растем 📉 %.2f %%" % percent
        else:
            bid = regular_market_previous_close
            message = "Рынок закрыт\nЦена закрытия: " + f"{abs(int(bid)):,}" + '₽'
        # Считаем прибыль
        data = {
            'roman': {'name': 'Роман', 'stock_num': 205, 'avg_price': 1851},
            'ivan': {'name': 'Вано', 'stock_num': 195, 'avg_price': 1627},
            'nikolay': {'name': 'Пакетя', 'stock_num': 25, 'avg_price': 1890},
            #'serega': {'name': 'Красавчик', 'stock_num': 28, 'avg_price': 2036},
            #'brat_koli': {'name': 'Брат Коли', 'stock_num': 40, 'avg_price': 1944},
            'dima': {'name': 'Dimasique', 'stock_num': 3, 'avg_price': 1652},
            'kirienko': {'name': 'Mr.Kirienko', 'stock_num': 50000, 'avg_price': 962}
        }

        balance = 0
        overall_mail_holdings = 0
        overall_mail_investments = 0
        income_pcts = []
        message += '\n-'
        for key in data:
            income = data[key]['stock_num'] * bid - data[key]['stock_num'] * data[key]['avg_price']
            income_pct = ((bid - data[key]['avg_price']) / data[key]['avg_price']) * 100
            income_pcts.append({'name': data[key]['name'], 'income_pct': income_pct})
            personal_holdings = data[key]['stock_num'] * bid
            personal_investments = data[key]['stock_num'] * data[key]['avg_price']
            direction_pic = '🐠'
            # direction_text = ' всрал '
            direction_sign = '-'
            if income_pct < -10:
                direction_pic = '🐟'
            if income_pct < -15:
                direction_pic = '🦠'
            if income_pct < -25:
                direction_pic = '🍣'
            if income_pct < -35:
                direction_pic = '🗿'
            if income_pct < -50:
                direction_pic = '💩'
            if data[key]['avg_price'] < bid:
                direction_pic = '🦈'
                # direction_text = ' поднял '
                direction_sign = '+'
            message += '\n' + direction_pic + ' ' + data[key]['name'] + ' ' + direction_sign + \
                       f"{abs(int(income)):,}" + '₽ (' + direction_sign + str(abs(int(income_pct))) + '%)'
            # Статистика
            if key != 'kirienko':
                balance += income
                overall_mail_holdings += personal_holdings
                overall_mail_investments += personal_investments

        income_pcts_sorted = sorted(income_pcts, key = itemgetter('income_pct'))
        index = message.find(income_pcts_sorted[0].get('name'))
        message = message[:index-1] + '🥇' + message[index:]
        index = message.find(income_pcts_sorted[1].get('name'))
        message = message[:index-1] + '🥈' + message[index:]
        index = message.find(income_pcts_sorted[2].get('name'))
        message = message[:index-1] + '🥉' + message[index:]

        direction_stat = ' всрато '
        if balance > 0:
            direction_stat = ' поднято '
        take_money = '\n-\n' + '❌💩🥈Брат Коли -43,240₽ (-55%)' + '\n' + '❌💩🥇Красавчик -40,952₽ (-71%)'
        message += take_money + '\n-\n' + '💵 Инвестировано ' + f"{int(overall_mail_investments):,}" + '₽' + '\n💵 Текущая стоимость бумаг ' + f"{int(overall_mail_holdings):,}" + '₽' + \
                   '\n💰 Общими усилиями' + direction_stat + f"{abs(int(balance)):,}"  + '₽' 

        # Выводим результат
        context.bot.send_message(chat_id=update.effective_chat.id, text=message)
    except Exception as e:
        print(e)
        context.bot.send_message(chat_id=update.effective_chat.id, text="Stock market is not available")


def quote(update, context):
    f = forismatic.ForismaticPy()
    author = ''
    if f.get_Quote('ru')[1]:
        author = '\n- ' + f.get_Quote('ru')[1]
    message = '🔮 ' + f.get_Quote('ru')[0] + author
    context.bot.send_message(chat_id=update.effective_chat.id, text=message)


path = home_dir + 'kolya.png'
path_tmp = home_dir + 'kolya_tmp.png'
wrapper = textwrap.TextWrapper(width=35)

client = MongoClient("mongodb+srv://" + db_login_password + "@realmcluster.yzc9u.mongodb.net")
db = client['db']
collection = db['prod']


def send_quote(chat_id, message):
    font_size = 14 - int(len(message) / 50)
    unicode_font = ImageFont.truetype(home_dir + "DejaVuSans.ttf", font_size)
    im = Image.open(path)
    draw_text = ImageDraw.Draw(im)
    draw_text.text(
        (60, 45),
        message,
        font=unicode_font,
        fill='#1C0606'
    )
    im.save(path_tmp)
    updater.bot.send_photo(chat_id=chat_id, photo=open(path_tmp, 'rb'))


def kolya_wisdom(update, context):
    rnd = randint(0, 100)
    message = ""
    if rnd >= 0:
        for item in collection.find({"kolya_wisdom": 1}):
            message = wrapper.fill(text=choice(item["quotes"])) + "\n\n                       - Николай Бутенко"
    else:
        f = forismatic.ForismaticPy()
        author = ''
        if f.get_Quote('ru')[1]:
            author = '\n\n                       - ' + f.get_Quote('ru')[1]
        message = wrapper.fill(text=f.get_Quote('ru')[0]) + author
    send_quote(update.effective_chat.id, message)


def kolya_superdry(update, context):
    date_format = "%d.%m.%Y"
    message = ""
    if context.args:
        if update.message.from_user['id']:
            if int(update.message.from_user['id']) == int(kolya_superdry_allowed_user_id):
                try:
                    weight = round(float(context.args[0].replace(",", ".")), 2)
                    message = "⚖️ Сегодняшний вес - " + str(weight) + " кг"
                    today = date.today()
                    d1 = today.strftime(date_format)
                    query = {"date": d1}
                    values = {"kolya_superdry": 1, "date": d1, "weight": weight}

                    find_result = collection.find(query)
                    if find_result.count() == 0:
                        if collection.save(values):
                            message += "\n☁️ Успешно добавлен в ОБЛАЧНУЮ БД"
                    else:
                        if collection.update_one(query, {"$set": values}):
                            message += "\n☁️ Успешно обновлен в ОБЛАЧНОЙ БД"
                except:
                    message = "Что-то пошло не так"
            else:
                message = "🧔🏻 Нужно быть Колей, чтобы редактировать вес"
        context.bot.send_message(chat_id=update.effective_chat.id, text=message)
    else:
        message = "🏃‍♂️ Статистика марафона:\n"
        x_array = []
        y_array = []
        weight_list = list(collection.find({"kolya_superdry": 1}))
        for item in weight_list:
            # message += item['date'] + ' - ' + str(item['weight']) + ' кг\n'
            x_array.append(datetime(int(item['date'][6:10]), int(item['date'][3:5]), int(item['date'][:2])))
            y_array.append(item['weight'])
        number_of_days = datetime.strptime(weight_list[-1]['date'], date_format) - datetime.strptime(
            weight_list[0]['date'], date_format)
        number_of_days_including_current = number_of_days.days + 1
        message += '⚖️ Начало (' + str(weight_list[0]['date']) + ') - ' + str(weight_list[0]['weight']) + ' кг\n'
        message += '⚖️ Сейчас (' + str(weight_list[-1]['date']) + ') - ' + str(weight_list[-1]['weight']) + ' кг\n'
        weight_diff = weight_list[-1]['weight'] - weight_list[0]['weight']
        if weight_diff > 0:
            weight_diff_dir = '👎 Набрал '
        else:
            weight_diff_dir = '👍 Сбросил '
        message += weight_diff_dir + str(abs(round(weight_diff, 2))) + ' кг за ' + str(
            number_of_days_including_current) + ' дн.\n'
        message += '📋 В среднем по ' + str(
            abs(round((weight_diff / number_of_days_including_current), 2))) + ' кг в день'
        x_np_array = np.array(x_array)
        y_np_array = np.array(y_array)
        date_num = dates.date2num(x_np_array)
        # smooth
        date_num_smooth = np.linspace(date_num.min(), date_num.max())
        spl = make_interp_spline(date_num, y_np_array, k=1)
        y_np_smooth = spl(date_num_smooth)
        plt.cla()
        plt.xticks(rotation=45, ha='right')
        plt.plot(dates.num2date(date_num_smooth), y_np_smooth)
        plt.tight_layout()
        plt.savefig(home_dir + 'kolya_superdry.png')
        context.bot.send_photo(chat_id=update.effective_chat.id, photo=open(home_dir + 'kolya_superdry.png', 'rb'),
                               caption=message)


def kolya_history(update, context):
    if context.args:
        quotes = list(db.kolya_quotes_history.find({'msg': re.compile(context.args[0], re.IGNORECASE)}))
        if len(quotes) == 0:
            quotes = list([{'msg': 'Ничего не найдено по запросу', 'date': date.today()}])
    else:
        quotes = list(db.kolya_quotes_history.find({'msg': re.compile("^(ебать|бля|пиздец).{7,}", re.IGNORECASE)}))
    quote = choice(quotes)
    message = wrapper.fill(text=quote['msg']) + "\n\n           - Николай Бутенко, {}".format(
        quote['date'].strftime('%d.%m.%Y'))
    send_quote(update.effective_chat.id, message)


def calc_score(msg, last_user_id):
    text_score = min(len(msg.get('text', '') or ''), 50)
    sticker_score = len(msg.get('sticker_emoji', '') or '') * 10
    photo_score = (msg.get('with_photo', False) or 0) * 15
    new_msg_score = 5 * (msg['user_id'] != last_user_id)
    return text_score + sticker_score + photo_score + new_msg_score


def aggregate_all_pidor_stats(date_from, date_to) -> {}:
    logging.info("Aggregating from date: {}, to date: {}".format(date_from, date_to))

    last_user_id = 0

    all_scores = {}
    for msg in db.all_messages.find(filter={
        'date': {'$gte': date_from, '$lt': date_to}
    }, sort=[('date', 1), ('message_id', 1)]):
        chat_id = msg['chat_id']
        user_id = msg['user_id']

        scores = all_scores.get(chat_id, {})
        score = scores.get(user_id, 0)
        score += calc_score(msg, last_user_id)
        scores[user_id] = score
        all_scores[chat_id] = scores

        last_user_id = user_id

    result = {}
    for chat_id, scores in all_scores.items():
        result[chat_id] = sorted(scores.items(), key=lambda pair: pair[1], reverse=True)
    return result


def format_user_name(chat_id, user_id):
    try:
        user = updater.bot.get_chat_member(chat_id=chat_id, user_id=user_id).user
        user_name = " ".join(filter(None, [user.first_name, user.last_name]))
        if user_name == " ":
            user_name = user.username
    except Exception as e:
        logging.error("Can't get user name for chat id {} and user id {}: {}".format(chat_id, user_id, e))
        user_name = "{}".format(user_id)
    user_name = user_name.replace("_", "\\_")
    return user_name


def format_pidor_stats_body(scores, chat_id) -> "":
    lines = []
    for user_id, score in scores:
        lines.append("{}: {}".format(format_user_name(chat_id, user_id), score))
    for i, line in enumerate(lines):
        if i == len(lines) - 1:
            line = "👎 " + line
        elif i == 0:
            line = "👍 " + line
        else:
            line = "👌 " + line
        lines[i] = line
    return "\n".join(lines)


def monthly_pidor_so_far_raw(chat_id):
    date_to = datetime.now()
    if (date_to + timedelta(days=1)).month != date_to.month:
        updater.bot.send_message(chat_id=chat_id, text="В последний день месяца нельзя смотреть статистику!")
        return
    date_from = date_to.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    scores = aggregate_all_pidor_stats(date_from, date_to).get(chat_id)
    if scores is None:
        updater.bot.send_message(chat_id=chat_id, text="Недостаточно статистики :С")
        return

    body = "Рейтинг активности на звание пидора месяца в *{}*:\n".format(format_month(date_from))
    body += format_pidor_stats_body(scores, chat_id)
    updater.bot.send_message(chat_id=chat_id, text=body, parse_mode="markdown")


def monthly_pidor_so_far(update, context):
    logging.info("monthly_pidor_so_far: {}".format(update))
    monthly_pidor_so_far_raw(update.effective_chat.id)


def monthly_pidor_cron():
    now = datetime.now()
    if now.day != 1:
        return
    date_to = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    date_from = (date_to - timedelta(days=1)).replace(day=1)

    for chat_id, scores in aggregate_all_pidor_stats(date_from, date_to).items():
        send_pidor_winner_message(chat_id, date_from, scores)


def send_pidor_winner_message(chat_id, date_from, scores):
    winner_user_id, score = scores[len(scores) - 1]
    winner_name = format_user_name(chat_id, winner_user_id)
    body = "Пидором месяца в *{}* становится [{}](tg://user?id={}), проявив наименьшую активность с рейтингом *{}*! " \
           "Поздравляем победителя 🎉🎉🎉".format(format_month(date_from), winner_name, winner_user_id, score)
    body += "\nТаблица результатов:\n" + format_pidor_stats_body(scores, chat_id)
    updater.bot.send_message(chat_id=chat_id, text=body, parse_mode="markdown")


def format_month(d):
    return [
        '',
        'январе',
        'феврале',
        'марте',
        'апреле',
        'мае',
        'июне',
        'июле',
        'августе',
        'сентябре',
        'октябре',
        'ноябре',
        'декабре',
    ][d.month]


def all_messages_handler(update, context):
    msg = update.effective_message

    text = ""
    if msg.text is not None:
        text = msg.text
    sticker_emoji = ""
    if msg.sticker is not None:
        sticker_emoji = msg.sticker.emoji

    db.all_messages.update_one(
        {
            'chat_id': update.effective_chat.id,
            'message_id': msg.message_id,
        },
        {
            '$set': {
                'user_id': msg.from_user.id,
                'date': msg.date,
                'text': text,
                'sticker_emoji': sticker_emoji,
                'with_photo': len(msg.photo) > 0
            }
        }, upsert=True)


scheduler = BackgroundScheduler(timezone=pytz.timezone('Europe/Moscow'))
scheduler.add_job(monthly_pidor_cron, 'cron', hour=12, minute=0)
scheduler.start()

updater.dispatcher.add_handler(CommandHandler('start', start))
updater.dispatcher.add_handler(CommandHandler('dima', dima))
updater.dispatcher.add_handler(CommandHandler('mail', mail))
updater.dispatcher.add_handler(CommandHandler('vk', mail))
updater.dispatcher.add_handler(CommandHandler('quote', quote))
updater.dispatcher.add_handler(CommandHandler('kolya_wisdom', kolya_wisdom))
updater.dispatcher.add_handler(CommandHandler('kolya_superdry', kolya_superdry))
updater.dispatcher.add_handler(CommandHandler('kolya_history', kolya_history))
updater.dispatcher.add_handler(CommandHandler('monthly_pidor', monthly_pidor_so_far))
updater.dispatcher.add_handler(MessageHandler(Filters.update.messages & (~Filters.command), all_messages_handler))

updater.start_polling()
updater.idle()
