import logging
import sqlite3
import random
import threading
import traceback
import html
from flask import Flask, render_template, jsonify
from datetime import datetime
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, filters, MessageHandler, CallbackQueryHandler


###   ---   DB functions   ---   ###

## Creates the table and the db
def setup_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # Timestamps will be used to calculate some metrics
    cursor.execute('''
                    CREATE TABLE IF NOT EXISTS orders (
                        order_id INTEGER PRIMARY KEY,
                        product_id TEXT NOT NULL,
                        user_id TEXT NOT NULL,
                        rating INTEGER,
                        feedback TEXT,
                        created_ts TIMESTAMP NOT NULL,
                        rating_ts TIMESTAMP,
                        feedback_ts TIMESTAMP)''')
    conn.commit()
    conn.close()

## Simple function create an order on the db 
## with minimal info
def create_order(user_id: str):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    order_id = random.randint(100, 999)
    product_id = random.choice(["11", "12", "13", "14", "15"])
    created_ts = datetime.now()
    cursor.execute('''
                      INSERT INTO orders (order_id, product_id, user_id, created_ts)
                      VALUES (?, ?, ?, ?)''', (order_id, product_id, user_id, created_ts))
    
    conn.commit()
    conn.close()

## Given a user_id just return all the order id's associated with it 
## and rating null
def orders_user(user_id: str):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute('SELECT order_id FROM orders WHERE user_id = ? AND feedback IS NULL', (user_id,))
    rows = cursor.fetchall()

    order_ids = [str(row[0]) for row in rows]

    # Close the connection to the database
    conn.close()

    return order_ids

# Updates the rating of an order
def rate_order(order_id: int, rating: int):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    rating_ts = datetime.now()

    # No rating overriding
    cursor.execute('''
                      UPDATE orders
                      SET rating = ?, rating_ts = ?
                      WHERE order_id = ? AND rating IS NULL
                   ''', (rating, rating_ts, order_id))

    
    conn.commit()
    conn.close()

def review_order(order_id: int, feedback: str):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    feedback_ts = datetime.now()

    cursor.execute('''
    UPDATE orders
    SET feedback = ?, feedback_ts = ?
    WHERE order_id = ? AND feedback IS NULL
    ''', (feedback, feedback_ts, order_id))

    conn.commit()
    conn.close()

###   ---   Telegram bot   ---   ###

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# Error notifications will be sent to this chat_id (ie me)
DEVELOPER_CHAT_ID = 391559422

# Type '/order' on telegram bot to create an order
# TODO might present order_id clashes
async def order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    create_order(str(update.effective_chat.id))
    await context.bot.send_message(chat_id=update.effective_chat.id, text="New order created!")


async def conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id,text="This is a fake conversation, carry on or write 'Done' when ready")

async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # We only want the unrated orders as those are the ones 
    # we are going to update
    orders_ids = orders_user(str(update.effective_chat.id))
    if len(orders_ids) == 0:
        await update.message.reply_text("You have no unrated orders. Use the comand '/order' to create a new one")
    else:
        await update.message.reply_text("Pick an order to rate:",reply_markup=ReplyKeyboardMarkup([orders_ids],one_time_keyboard=True))

# Create the rating keyboard
async def order_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    context.user_data["choice"] = text
    keyboard = [[InlineKeyboardButton("5",callback_data=f"5,{text}"),
                 InlineKeyboardButton("4",callback_data=f"4,{text}"),
                 InlineKeyboardButton("3",callback_data=f"3,{text}"),
                 InlineKeyboardButton("2",callback_data=f"2,{text}"),
                 InlineKeyboardButton("1",callback_data=f"1,{text}")]]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Please rate:", reply_markup=reply_markup)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    # Get the rating and the order_id
    rate,orderid = int(query.data.split(",")[0]), int(query.data.split(",")[1])
    # Should check that the order is only updated by the user that created it
    rate_order(orderid,rating=rate)
    await query.edit_message_text(text=f"Selected option: {rate}")
    await context.bot.send_message(chat_id=update.effective_chat.id,text=f"Write a review for order {orderid} by beggining your next message with\n 'Review {orderid}:' and then write your review")

async def review(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    # We can do this because of the clause the regex will match
    order_id = text.split(":")[0][-3:]
    # In case there's more tan one ':'
    feedback = " ".join(text.split(":")[1:])
    # Same case, must check if the user updating the order is the same one that crerated it
    review_order(int(order_id),feedback)
    await context.bot.send_message(chat_id=update.effective_chat.id,text="Thanks for your review!")


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id,text="your chat id is {}".format(update.effective_chat.id))

# This will catch telegrram errors and will let me know
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)

    update_str = update.to_dict() if isinstance(update, Update) else str(update)
    message = (
        f"An exception was raised while handling an update\n"
        f"<pre>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}"
        "</pre>\n\n"
        f"<pre>context.chat_data = {html.escape(str(context.chat_data))}</pre>\n\n"
        f"<pre>context.user_data = {html.escape(str(context.user_data))}</pre>\n\n"
        f"<pre>{html.escape(tb_string)}</pre>"
    )

    await context.bot.send_message(
        chat_id=DEVELOPER_CHAT_ID, text=message, parse_mode=ParseMode.HTML
    )



###   ---   Webapp   ---   ###
app = Flask(__name__)

@app.route("/")
def index():
    return render_template('index.html')

@app.route("/api/orders", methods=["GET"])
def get_orders():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT order_id, product_id, user_id, rating, feedback, created_ts, rating_ts, feedback_ts FROM orders')
    rows = cursor.fetchall()
    conn.close()

    orders = []
    for row in rows:
        orders.append({
            "order_id": row[0],
            "product_id": row[1],
            "user_id": row[2],
            "rating": row[3],
            "feedback": row[4],
            "created_ts": row[5],
            "rating_ts": row[6],
            "feedback_ts": row[7]
        })

    return jsonify(orders)

if __name__ == '__main__':

    setup_db()
    #create_order("391559422")
    #create_order("391559422")
    
    # Not safe at all, I know
    application = ApplicationBuilder().token('6000699537:AAHw3ZE5BEjwRw-9o_xJ_UCBZF5uFt-3qZ0').build()
    
    order_handler = CommandHandler('order', order)
    help_handler = CommandHandler('help',help)
    done_handler = MessageHandler(filters.Regex("^Done$"),done)
    order_choice_handler = MessageHandler(filters.Regex("\d{3}"),order_choice)
    review_handler = MessageHandler(filters.Regex("^Review \d{3}:"),review)
    conversation_handler = MessageHandler(filters.TEXT & (~filters.COMMAND | 
                                                          filters.Regex("^Done$") | 
                                                          filters.Regex("^\d{3}") |
                                                          filters.Regex("^Review \d{3}:")), conversation)
    application.add_handler(order_handler)
    application.add_handler(help_handler)
    application.add_handler(done_handler)
    application.add_handler(review_handler)
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(order_choice_handler)
    application.add_handler(conversation_handler)
    application.add_error_handler(error_handler)
    
    class FlaskThread(threading.Thread):
        def run(self) -> None:
            app.run(host="0.0.0.0", port="8000")

    flask_thread = FlaskThread()
    flask_thread.start()

    application.run_polling()
