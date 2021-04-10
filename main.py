from telegram.ext import Updater, CommandHandler
from datetime import datetime as dt
from yfinance import Ticker
from forismatic import *
from PIL import Image, ImageDraw, ImageFont
import textwrap
from dotenv import dotenv_values
from pymongo import MongoClient
from random import choice, randint
from datetime import date
import matplotlib.pyplot as plt
import numpy as np

config = dotenv_values("conf.env")
bot_token = config['bot_token']  #prostavushka_bot
chat_id = config['bot_token']  #chat_id Amsterdam
db_conf = config['db']
db_login_password = config['db_login_password']
kolya_superdry_allowed_user_id = config['kolya_superdry_allowed_user_id']
home_dir = config['home_dir']

updater = Updater(token=bot_token, use_context=True)  #запуск экземпляра бота

dispatcher = updater.dispatcher

def start(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="I'm ProstavushkaBot, supported commands:"
                                                                    "/dima - Time since @usebooz started his project")
def dima(update, context):
    start = dt.fromtimestamp(1615969080)
    end = dt.now()
    elapsed=end-start
    context.bot.send_message(chat_id=update.effective_chat.id, text="Time since @usebooz started his project: %02d days %02d hours %02d minutes %02d seconds" % (elapsed.days, elapsed.seconds // 3600, elapsed.seconds // 60 % 60, elapsed.seconds % 60))

def mail(update, context):
    try:
        mail_info =Ticker("MAIL.ME").info
        bid = float(mail_info["regularMarketPrice"])
        regularMarketPreviousClose = float(mail_info["regularMarketPreviousClose"])
        if bid != 0:
            change = regularMarketPreviousClose/bid
            message = "Mail.ru price: %02d ₽\nregularMarketPreviousClose: %02d ₽\n" % (bid, regularMarketPreviousClose)
            percent = ((bid - regularMarketPreviousClose) / regularMarketPreviousClose) * 100
            if percent > 0:
                message += "upwards trend 📈 +%.2f %%"  % percent
            else:
                message += "downwards trend 📉 %.2f %%"  % percent
        else:
            bid = regularMarketPreviousClose
            message = "Рынок закрыт\nЦена закрытия: " + f"{abs(int(bid)):,}" + '₽'
        # Считаем прибыль
        data = {
        'roman': {'name': 'Роман', 'stock_num': 205, 'avg_price': 1851},
        'ivan': {'name': 'Вано', 'stock_num': 95, 'avg_price': 1996},
        'nikolay': {'name': 'Пакетя', 'stock_num': 25, 'avg_price': 1890},
        'serega': {'name': 'Красавчик', 'stock_num': 28, 'avg_price': 2036},
        'brat_koli': {'name': 'Брат Коли', 'stock_num': 40, 'avg_price': 1944}
        }

        balance = 0
        overall_mail_holdings = 0

        message += '\n-'
        for key in data:
            direction_pic = '🐠'
            direction_text = ' всрал '
            if data[key]['avg_price'] < bid:
                direction_pic = '🦈'
                direction_text = ' поднял '
            income = data[key]['stock_num'] * bid - data[key]['stock_num'] * data[key]['avg_price']
            message += '\n' + direction_pic + ' ' + data[key]['name'] + direction_text + f"{abs(int(income)):,}" + '₽'
            # Статистика
            balance += income
            overall_mail_holdings += data[key]['stock_num'] * bid

        direction_stat = ' всрато '
        if balance > 0:
            direction_stat = ' поднято '
        message += '\n-\n' + '💰 Общими усилиями' + direction_stat + f"{abs(int(balance)):,}" + '₽\n💵 По текущему курсу инвестировано ' + f"{int(overall_mail_holdings):,}" + '₽'
        
        # Выводим результат
        context.bot.send_message(chat_id=update.effective_chat.id, text=message)
    except:
        context.bot.send_message(chat_id=update.effective_chat.id, text="Stock market is not available")

def quote(update, context):
    f = forismatic.ForismaticPy()
    author = ''
    if f.get_Quote('ru')[1]:
        author = '\n- ' + f.get_Quote('ru')[1]
    message = '🔮 ' + f.get_Quote('ru')[0] + author
    context.bot.send_message(chat_id=update.effective_chat.id, text=message)

path = '/home/ubuntu/prostavushka_bot/kolya.png'
path_tmp = '/home/ubuntu/prostavushka_bot/kolya_tmp.png'
wrapper = textwrap.TextWrapper(width=35)

client = MongoClient("mongodb+srv://" + db_login_password + "@realmcluster.yzc9u.mongodb.net/" + db_conf)
db = client['db']
collection = db[db_conf]

def kolya_wisdom (update, context):
    rnd = randint(0,100)
    if rnd >= 0:
        for item in collection.find({"kolya_wisdom": 1}):
            message = wrapper.fill(text=choice(item["quotes"])) + "\n\n                       - Николай Бутенко"
    else:
        f = forismatic.ForismaticPy()
        author = ''
        if f.get_Quote('ru')[1]:
            author = '\n\n                       - ' + f.get_Quote('ru')[1]
        message = wrapper.fill(text=f.get_Quote('ru')[0]) + author
    font_size = 14 - int(len(message)/50);
    unicode_font = ImageFont.truetype("/home/ubuntu/prostavushka_bot/DejaVuSans.ttf", font_size)
    im = Image.open(path)
    draw_text = ImageDraw.Draw(im)
    draw_text.text(
        (60,45),
        message,
        font=unicode_font,
        fill=('#1C0606')
        )
    im.save(path_tmp)
    context.bot.send_photo(chat_id=update.effective_chat.id, photo=open(path_tmp, 'rb'))

def kolya_superdry (update, context):
    if context.args:
        if update.message.from_user['id']: 
            if int(update.message.from_user['id']) == int(kolya_superdry_allowed_user_id):
                try:
                    weight = round(float(context.args[0].replace(",",".")),2)
                    message = "⚖️ Сегодняшний вес - " + str(weight) + " кг"
                    today = date.today()
                    d1 = today.strftime("%d.%m.%Y")
                    query = {"date": d1}
                    values = {"kolya_superdry": 1,"date": d1,"weight": weight}

                    find_result = collection.find(query)
                    if find_result.count() == 0:
                        if collection.save(values):
                            message += "\n☁️ Успешно добавлен в ОБЛАЧНУЮ БД"
                    else:
                        if collection.update_one(query, { "$set": values}):
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
        for item in collection.find({"kolya_superdry": 1}):
            message += item['date'] + ' - ' + str(item['weight']) + ' кг\n'
            x_array.append(item['date'])
            y_array.append(item['weight'])
        x_np_array = np.array(x_array)
        y_np_array = np.array(y_array)
        plt.cla()
        plt.plot(x_np_array,y_np_array)
        plt.savefig(home_dir + 'kolya_superdry.png')
        context.bot.send_message(chat_id=update.effective_chat.id, text=message)
        context.bot.send_photo(chat_id=update.effective_chat.id, photo=open(home_dir + 'kolya_superdry.png', 'rb'))

start_handler = CommandHandler('start', start)
dispatcher.add_handler(start_handler)
dima_handler = CommandHandler('dima', dima)
dispatcher.add_handler(dima_handler)
dima_handler = CommandHandler('mail', mail)
dispatcher.add_handler(dima_handler)
quote_handler = CommandHandler('quote', quote)
dispatcher.add_handler(quote_handler)
kolya_wisdom_handler = CommandHandler('kolya_wisdom', kolya_wisdom)
dispatcher.add_handler(kolya_wisdom_handler)
kolya_superdry_handler = CommandHandler('kolya_superdry', kolya_superdry)
dispatcher.add_handler(kolya_superdry_handler)

updater.start_polling()
