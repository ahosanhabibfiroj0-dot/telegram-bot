import telebot
from telebot.types import *
import sqlite3
import os

TOKEN = "8738759140:AAEpCdC1E82f_ai6K-m-6pu2sXWid4h1v7k"
ADMIN_ID =7429993190

bot = telebot.TeleBot(TOKEN)

# ================= DATABASE =================
conn = sqlite3.connect("bot.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""CREATE TABLE IF NOT EXISTS users(
id INTEGER PRIMARY KEY,
name TEXT,
username TEXT,
balance REAL DEFAULT 0,
deposited REAL DEFAULT 0,
spent_today REAL DEFAULT 0,
total_spent REAL DEFAULT 0,
banned INTEGER DEFAULT 0
)""")

cur.execute("CREATE TABLE IF NOT EXISTS stock(product TEXT, account TEXT)")

# NEW DEPOSIT TABLE
cur.execute("""CREATE TABLE IF NOT EXISTS deposits(
id INTEGER PRIMARY KEY AUTOINCREMENT,
user_id INTEGER,
amount INTEGER,
method TEXT,
trx TEXT,
status TEXT
)""")

conn.commit()

# ================= MEMORY =================
user_product = {}
admin_upload_mode = {}
clear_mode = {}

# ================= PAYMENT =================
PAYMENT_NUMBERS = {
    "bKash": "01340808501",
    "Nagad": "01340808501",
    "Rocket": "01910781563"
}

# ================= MENU =================
def main_menu():
    m = ReplyKeyboardMarkup(resize_keyboard=True)
    m.row("🛍️ Shop Now","💰 Deposit")
    m.row("🙎🏻‍♂️ Profile","🎁 Refer")
    m.row("📞 Support")
    return m

def main_menu_admin():
    m = main_menu()
    m.row("↪️ADMIN PANEL↩️")
    return m

# ================= USER =================
def get_user(uid):
    cur.execute("SELECT * FROM users WHERE id=?", (uid,))
    return cur.fetchone()

def profile_text(u):
    return f"""👤 Name: {u[1]}
🆔 User ID: {u[0]}
👤 Username: @{u[2]}
💰 Balance: {u[3]} TK
💵 Deposited today: {u[4]} TK
🧾 Spent today: {u[5]} TK
📦 Total spent: {u[6]} TK"""

# ================= START =================
@bot.message_handler(commands=['start'])
def start(msg):
    u = msg.from_user
    cur.execute("INSERT OR IGNORE INTO users VALUES(?,?,?,?,?,?,?,?)",
                (u.id,u.first_name,u.username,0,0,0,0,0))
    conn.commit()

    if msg.chat.id == ADMIN_ID:
        bot.send_message(msg.chat.id, profile_text(get_user(msg.chat.id)), reply_markup=main_menu_admin())
    else:
        bot.send_message(msg.chat.id, profile_text(get_user(msg.chat.id)), reply_markup=main_menu())

# ================= SHOP =================
@bot.message_handler(func=lambda m: m.text=="🛍️ Shop Now")
def shop(msg):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("Hotmail Trust","Outlook Trust")
    kb.row("Fresh Gmail","🎓 Edu Mail")
    kb.row("◀️ Back")
    bot.send_message(msg.chat.id,"🛍️ Choose a product:", reply_markup=kb)

PRICE = 1.2

def show_product(chat_id, product):
    cur.execute("SELECT COUNT(*) FROM stock WHERE product=?", (product,))
    total = cur.fetchone()[0]

    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🛍️ Single Buy")
    kb.row("📦 Bulk Buy")
    kb.row("◀️ Back")

    user_product[chat_id] = product

    bot.send_message(chat_id,f"""🎓 {product}
💰 Price: {PRICE} TK

📁 File Stock: {total}
📊 Total: {total}""", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text in ["Hotmail Trust","Outlook Trust"])
def product(msg):
    show_product(msg.chat.id, msg.text)

@bot.message_handler(func=lambda m: m.text in ["Fresh Gmail","🎓 Edu Mail"])
def off(msg):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("◀️ Back")
    bot.send_message(msg.chat.id,"🎁 ════OFF════", reply_markup=kb)

# ================= BUY =================
def get_stock(product, qty):
    cur.execute("SELECT account FROM stock WHERE product=? LIMIT ?", (product, qty))
    return [x[0] for x in cur.fetchall()]

def remove_stock(product, qty):
    cur.execute("DELETE FROM stock WHERE rowid IN (SELECT rowid FROM stock WHERE product=? LIMIT ?)", (product, qty))
    conn.commit()

@bot.message_handler(func=lambda m: m.text=="🛍️ Single Buy")
def single(msg):
    uid = msg.chat.id
    product = user_product.get(uid)
    u = get_user(uid)

    if u[3] < PRICE:
        bot.send_message(uid,f"❌ Need {PRICE} TK")
        return

    data = get_stock(product,1)
    if not data:
        bot.send_message(uid,"❌ Out of stock")
        return

    remove_stock(product,1)
    cur.execute("UPDATE users SET balance=balance-? WHERE id=?", (PRICE,uid))
    conn.commit()

    bot.send_message(uid,f"✅ {data[0]}")

@bot.message_handler(func=lambda m: m.text=="📦 Bulk Buy")
def bulk(msg):
    bot.send_message(msg.chat.id,"📦 Enter quantity:")
    bot.register_next_step_handler(msg, bulk2)

def bulk2(msg):
    uid = msg.chat.id
    try:
        qty = int(msg.text)
    except:
        bot.send_message(uid,"❌ Invalid number")
        return

    product = user_product.get(uid)
    cost = qty * PRICE

    u = get_user(uid)
    if u[3] < cost:
        bot.send_message(uid,"❌ Balance low")
        return

    data = get_stock(product,qty)
    if len(data) < qty:
        bot.send_message(uid,"❌ Stock low")
        return

    remove_stock(product,qty)
    cur.execute("UPDATE users SET balance=balance-? WHERE id=?", (cost,uid))
    conn.commit()

    file = f"{uid}.txt"
    open(file,"w").write("\n".join(data))
    bot.send_document(uid, open(file,"rb"))
    os.remove(file)

# ================= NEW DEPOSIT =================
@bot.message_handler(func=lambda m: m.text=="💰 Deposit")
def deposit_start(msg):
    bot.send_message(msg.chat.id,"💵 Enter amount:")
    bot.register_next_step_handler(msg, get_amount)

def get_amount(msg):
    try:
        amount = int(msg.text)

        kb = ReplyKeyboardMarkup(resize_keyboard=True)
        kb.row("bKash","Nagad")
        kb.row("🚀 Rocket")
        kb.row("◀️ Back")

        bot.send_message(msg.chat.id,"Select payment method:", reply_markup=kb)
        bot.register_next_step_handler(msg, get_method, amount)

    except:
        bot.send_message(msg.chat.id,"❌ Enter valid amount")

def get_method(msg, amount):
    if msg.text == "◀️ Back":
        start(msg)
        return

    method = msg.text.replace("🚀 ","")

    if method not in PAYMENT_NUMBERS:
        bot.send_message(msg.chat.id,"❌ Wrong method")
        return

    number = PAYMENT_NUMBERS[method]

    bot.send_message(msg.chat.id,
        f"{method}: {number}\nAmount: {amount}\n\n📸 Screenshot দিন")

    bot.register_next_step_handler(msg, get_ss, amount, method)

def get_ss(msg, amount, method):
    if not msg.photo:
        bot.send_message(msg.chat.id,"❌ Screenshot দিন")
        return

    file_id = msg.photo[-1].file_id

    cur.execute("INSERT INTO deposits(user_id,amount,method,trx,status) VALUES(?,?,?,?,?)",
                (msg.chat.id,amount,method,file_id,"pending"))
    conn.commit()

    dep_id = cur.lastrowid

    bot.send_photo(ADMIN_ID,file_id,
        caption=f"Deposit\nID:{dep_id}\nUser:{msg.chat.id}\nAmount:{amount}\nMethod:{method}\n/approve_{dep_id}")

    bot.send_message(msg.chat.id,"⏳ Pending approval")

@bot.message_handler(func=lambda m: m.text.startswith("/approve_"))
def approve(msg):
    if msg.chat.id != ADMIN_ID:
        return

    dep_id = int(msg.text.split("_")[1])

    cur.execute("SELECT user_id,amount FROM deposits WHERE id=?", (dep_id,))
    data = cur.fetchone()

    if not data:
        bot.send_message(msg.chat.id,"❌ Invalid ID")
        return

    uid, amount = data

    cur.execute("UPDATE deposits SET status='approved' WHERE id=?", (dep_id,))
    cur.execute("UPDATE users SET balance=balance+?, deposited=deposited+? WHERE id=?", (amount,amount,uid))
    conn.commit()

    bot.send_message(uid,f"✅ {amount} TK added")
    bot.send_message(msg.chat.id,"Approved")

# ================= BACK =================
@bot.message_handler(func=lambda m: m.text in ["◀️ Back"])
def back(msg):
    if msg.chat.id == ADMIN_ID:
        bot.send_message(msg.chat.id,"Back", reply_markup=main_menu_admin())
    else:
        bot.send_message(msg.chat.id,"Back", reply_markup=main_menu())

print("BOT RUNNING...")
bot.infinity_polling()
