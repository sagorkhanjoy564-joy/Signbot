import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ⚠️ এখানে আপনার নতুন Token বসান
BOT_TOKEN = "এখানে_TOKEN_বসান"

# আপনার Telegram Chat ID (অ্যাডমিন)
ADMIN_ID = 6214925940

logging.basicConfig(level=logging.INFO)

# পণ্যের তালিকা — দাম অ্যাডমিন কমান্ড দিয়ে সেট করা যাবে
products = {
    "1": {"name": "Sign Copy 10", "price": 0},
    "2": {"name": "Sign Copy 12", "price": 0},
    "3": {"name": "Sign Copy 13", "price": 0},
    "4": {"name": "Sign Copy 17", "price": 0},
}

# সাপ্লায়ারদের তালিকা
all_suppliers = {
    "S1": {"name": "সাপ্লায়ার ১", "chat_id": 0},
    "S2": {"name": "সাপ্লায়ার ২", "chat_id": 0},
    "S3": {"name": "সাপ্লায়ার ৩", "chat_id": 0},
    "S4": {"name": "সাপ্লায়ার ৪", "chat_id": 0},
}

# প্রতিটা পণ্যের সক্রিয় সাপ্লায়ার
active_suppliers = {}

# অর্ডার সংরক্ষণ
pending_orders = {}


def get_supplier_key_by_chat(chat_id):
    for key, s in all_suppliers.items():
        if s["chat_id"] == chat_id:
            return key
    return None

def get_order_by_supplier(supplier_key):
    for order_id, order in pending_orders.items():
        if order.get("supplier_key") == supplier_key and not order.get("confirmed"):
            return order_id, order
    return None, None


# ───── কাস্টমার ─────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["1. Sign Copy 10", "2. Sign Copy 12"], ["3. Sign Copy 13", "4. Sign Copy 17"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    product_list = "\n".join([
        f"{k}. {v['name']} — {'৳'+str(v['price']) if v['price'] > 0 else 'দাম জানতে অর্ডার করুন'}"
        for k, v in products.items()
    ])
    await update.message.reply_text(
        f"স্বাগতম! 🛍️\n\nআমাদের পণ্যসমূহ:\n\n{product_list}\n\nঅর্ডার করতে 1/2/3/4 লিখুন",
        reply_markup=reply_markup
    )


# ───── অ্যাডমিন কমান্ড ─────

async def set_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/setprice 1 500 — পণ্য ১ এর দাম ৫০০ সেট করুন"""
    if update.message.chat_id != ADMIN_ID:
        return
    args = context.args
    if len(args) != 2:
        await update.message.reply_text("ফরম্যাট: /setprice [পণ্য নম্বর] [দাম]\nউদাহরণ: /setprice 1 500")
        return
    key, price = args[0], args[1]
    if key not in products:
        await update.message.reply_text("পণ্য নম্বর ১-৪ এর মধ্যে দিন।")
        return
    products[key]["price"] = int(price)
    await update.message.reply_text(f"✅ {products[key]['name']} এর দাম ৳{price} সেট হয়েছে!")

async def set_supplier_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/setsupplier 1 S2 — পণ্য ১ এর সাপ্লায়ার S2 সেট করুন"""
    if update.message.chat_id != ADMIN_ID:
        return
    args = context.args
    if len(args) != 2:
        await update.message.reply_text("ফরম্যাট: /setsupplier [পণ্য নম্বর] [সাপ্লায়ার কোড]\nউদাহরণ: /setsupplier 1 S2")
        return
    product_key, supplier_key = args[0], args[1]
    if product_key not in products or supplier_key not in all_suppliers:
        await update.message.reply_text("পণ্য (1-4) বা সাপ্লায়ার কোড (S1-S4) ভুল।")
        return
    active_suppliers[product_key] = supplier_key
    await update.message.reply_text(
        f"✅ {products[product_key]['name']} → {all_suppliers[supplier_key]['name']}"
    )

async def add_supplier(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/addsupplier S1 123456789 নাম — সাপ্লায়ার যোগ করুন"""
    if update.message.chat_id != ADMIN_ID:
        return
    args = context.args
    if len(args) < 3:
        await update.message.reply_text("ফরম্যাট: /addsupplier [কোড] [chat_id] [নাম]\nউদাহরণ: /addsupplier S1 987654321 রহিম")
        return
    key, chat_id, name = args[0], int(args[1]), " ".join(args[2:])
    if key not in all_suppliers:
        await update.message.reply_text("কোড S1/S2/S3/S4 এর মধ্যে দিন।")
        return
    all_suppliers[key] = {"name": name, "chat_id": chat_id}
    await update.message.reply_text(f"✅ {key}: {name} (ID: {chat_id}) যোগ হয়েছে!")

async def remove_supplier_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/removesupplier 1 — পণ্য ১ এর সাপ্লায়ার সরান"""
    if update.message.chat_id != ADMIN_ID:
        return
    args = context.args
    if len(args) != 1 or args[0] not in products:
        await update.message.reply_text("ফরম্যাট: /removesupplier [পণ্য নম্বর]")
        return
    if args[0] in active_suppliers:
        del active_suppliers[args[0]]
        await update.message.reply_text(f"✅ {products[args[0]]['name']} এর সাপ্লায়ার সরানো হয়েছে।")
    else:
        await update.message.reply_text("কোনো সক্রিয় সাপ্লায়ার নেই।")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/status — সব কিছুর অবস্থা দেখুন"""
    if update.message.chat_id != ADMIN_ID:
        return
    msg = "📊 বর্তমান অবস্থা:\n\n"
    for key, product in products.items():
        price = f"৳{product['price']}" if product['price'] > 0 else "দাম নেই"
        if key in active_suppliers:
            supplier = all_suppliers[active_suppliers[key]]
            msg += f"✅ {product['name']} ({price}) → {supplier['name']}\n"
        else:
            msg += f"❌ {product['name']} ({price}) → সাপ্লায়ার নেই\n"
    msg += f"\n📦 পেন্ডিং অর্ডার: {len(pending_orders)}\n\n"
    msg += "👥 সাপ্লায়ার তালিকা:\n"
    for key, s in all_suppliers.items():
        status_mark = "✅" if s["chat_id"] != 0 else "❌"
        msg += f"{status_mark} {key}: {s['name']} (ID: {s['chat_id']})\n"
    await update.message.reply_text(msg)

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat_id != ADMIN_ID:
        return
    await update.message.reply_text(
        "📋 অ্যাডমিন কমান্ড:\n\n"
        "/status — সব অবস্থা দেখুন\n"
        "/setprice 1 500 — পণ্য ১ এর দাম সেট করুন\n"
        "/addsupplier S1 [chat_id] [নাম] — সাপ্লায়ার যোগ করুন\n"
        "/setsupplier 1 S1 — পণ্য ১ এ সাপ্লায়ার S1 সেট করুন\n"
        "/removesupplier 1 — পণ্য ১ এর সাপ্লায়ার সরান\n"
        "/help — এই সাহায্য দেখুন"
    )


# ───── মেসেজ হ্যান্ডলার ─────

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user = update.message.from_user
    chat_id = update.message.chat_id

    # পণ্য নম্বর চেক
    product_key = None
    for key in products:
        if text == key or text.startswith(key + "."):
            product_key = key
            break

    if product_key:
        product = products[product_key]

        if product_key not in active_suppliers:
            await update.message.reply_text(
                f"দুঃখিত! {product['name']} এখন স্টকে নেই। 😔\nপরে আবার চেষ্টা করুন।"
            )
            return

        supplier_key = active_suppliers[product_key]
        supplier = all_suppliers[supplier_key]
        order_id = f"ORD{chat_id}{product_key}"
        price_text = f"৳{product['price']}" if product['price'] > 0 else "দাম পরে জানানো হবে"

        await update.message.reply_text(
            f"✅ অর্ডার পেয়েছি!\n\n"
            f"পণ্য: {product['name']}\n"
            f"মূল্য: {price_text}\n\n"
            f"সাপ্লায়ারকে জানাচ্ছি... 🔄\n"
            f"PDF ফাইল পেলে আপনাকে পাঠিয়ে দেব। 📄"
        )

        pending_orders[order_id] = {
            "customer_id": chat_id,
            "customer_name": user.first_name,
            "product": product,
            "supplier_key": supplier_key,
            "confirmed": False,
        }

        try:
            await context.bot.send_message(
                chat_id=supplier["chat_id"],
                text=f"🛒 নতুন অর্ডার!\n\n"
                     f"অর্ডার ID: {order_id}\n"
                     f"কাস্টমার: {user.first_name}\n"
                     f"পণ্য: {product['name']}\n"
                     f"মূল্য: {price_text}\n\n"
                     f"📄 PDF পাঠান অথবা:\n"
                     f"✅ confirm {order_id}\n"
                     f"❌ cancel {order_id}"
            )
        except Exception as e:
            await update.message.reply_text("⚠️ সাপ্লায়ারের সাথে যোগাযোগ হয়নি।")
            logging.error(f"Supplier error: {e}")

    elif text.startswith("confirm "):
        order_id = text.split(" ")[1]
        if order_id not in pending_orders:
            await update.message.reply_text("❌ অর্ডার খুঁজে পাওয়া যায়নি।")
            return
        order = pending_orders[order_id]
        order["confirmed"] = True
        price_text = f"৳{order['product']['price']}" if order['product']['price'] > 0 else ""
        await context.bot.send_message(
            chat_id=order["customer_id"],
            text=f"🎉 অর্ডার কনফার্ম!\n\nপণ্য: {order['product']['name']}\n{price_text}\nPDF ফাইল শীঘ্রই পাবেন। 📄"
        )
        await update.message.reply_text("✅ কনফার্ম! এখন PDF পাঠান।")

    elif text.startswith("cancel "):
        order_id = text.split(" ")[1]
        if order_id not in pending_orders:
            await update.message.reply_text("❌ অর্ডার খুঁজে পাওয়া যায়নি।")
            return
        order = pending_orders[order_id]
        await context.bot.send_message(
            chat_id=order["customer_id"],
            text=f"😔 দুঃখিত! আপনার অর্ডার বাতিল হয়েছে।\nপরে আবার চেষ্টা করুন।"
        )
        await update.message.reply_text("❌ বাতিল করা হয়েছে।")
        del pending_orders[order_id]

    else:
        await update.message.reply_text("অর্ডার করতে 1, 2, 3 বা 4 লিখুন।\n/start দিয়ে তালিকা দেখুন।")


# ───── PDF হ্যান্ডলার ─────

async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    supplier_key = get_supplier_key_by_chat(chat_id)
    if not supplier_key:
        await update.message.reply_text("❌ আপনি সাপ্লায়ার হিসেবে রেজিস্টার্ড নন।")
        return

    order_id, order = get_order_by_supplier(supplier_key)
    if not order:
        await update.message.reply_text("⚠️ কোনো সক্রিয় অর্ডার নেই।")
        return

    file_id = update.message.document.file_id

    await context.bot.send_document(
        chat_id=order["customer_id"],
        document=file_id,
        caption=f"📄 আপনার অর্ডারের ফাইল!\n\nপণ্য: {order['product']['name']}\nঅর্ডার ID: {order_id}"
    )

    await update.message.reply_text(
        f"✅ PDF কাস্টমারকে পাঠানো হয়েছে!\nকাস্টমার: {order['customer_name']}"
    )

    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"📄 PDF ডেলিভারি সম্পন্ন!\n\nঅর্ডার: {order_id}\nপণ্য: {order['product']['name']}\nকাস্টমার: {order['customer_name']}\nসাপ্লায়ার: {all_suppliers[supplier_key]['name']}"
    )

    del pending_orders[order_id]


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("setprice", set_price))
    app.add_handler(CommandHandler("setsupplier", set_supplier_cmd))
    app.add_handler(CommandHandler("addsupplier", add_supplier))
    app.add_handler(CommandHandler("removesupplier", remove_supplier_cmd))
    app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("✅ বট চালু হয়েছে!")
    app.run_polling()

if __name__ == "__main__":
    main()
