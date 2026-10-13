import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
    ConversationHandler,
)
from keep_alive import keep_alive

# إعداد السجلات
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# ----------------- الإعدادات الأساسية -----------------
BOT_TOKEN = os.environ.get("BOT_TOKEN")      
ADMIN_CHAT_ID = 5083873437

PAYMENT_DETAILS = (
    "💳 **طرق الدفع المتوفرة:**\n\n"
    "1️⃣ **BaridiMob / CCP:**\n"
    "• RIP / الحساب: `00799999002815170969`\n"
    "• الاسم: Khedir Chaouki Abdeldjaouad\n\n"
    "2️⃣ **RedotPay:**\n"
    "• المعرف (ID): `1616018708`\n\n"
    "📌 بعد إتمام الدفع، يرجى **إرسال صورة أو ملف الوصل (PDF/Reçu) هنا مباشرة**."
)

PRODUCTS = {
    "gemini_pro": {"name": "اشتراك Gemini Pro", "price": "700 دج"},
    "canva_pro": {"name": "اشتراك Canva Pro (سنة)", "price": "400 دج"},
    "chatgpt_plus": {"name": "اشتراك ChatGPT Plus", "price": "2000 دج"},
}

CHOOSING_PRODUCT, WAITING_RECEIPT = range(2)

# ----------------- دوال الزبون (الطلب والدفع) -----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = [
        [InlineKeyboardButton(f"{info['name']} - {info['price']}", callback_data=key)]
        for key, info in PRODUCTS.items()
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "👋 أهلاً بك في متجر **Digital Products 55**!\n\n"
        "اختر المنتج أو الاشتراك الذي تريده من القائمة أدناه:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return CHOOSING_PRODUCT

async def product_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    selected_key = query.data
    product = PRODUCTS.get(selected_key)
    
    context.user_data['selected_product'] = product['name']
    context.user_data['selected_product_key'] = selected_key 
    context.user_data['price'] = product['price']

    message_text = (
        f"✅ لقد اخترت: **{product['name']}**\n"
        f"💰 المبلغ المطلوب: **{product['price']}**\n\n"
        f"{PAYMENT_DETAILS}"
    )

    await query.edit_message_text(text=message_text, parse_mode="Markdown")
    return WAITING_RECEIPT

async def receive_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    product_name = context.user_data.get('selected_product', 'منتج غير محدد')
    product_key = context.user_data.get('selected_product_key', 'unknown')
    price = context.user_data.get('price', '')

    admin_caption = (
        "🚨 **طلب شراء جديد!**\n\n"
        f"👤 الزبون: {user.full_name}\n"
        f"🆔 معرف الزبون: `{user.id}`\n"
        f"📦 المنتج: **{product_name}** ({price})\n\n"
        "إثبات الدفع مرفق 👆. يرجى الاختيار:"
    )

    admin_keyboard = [
        [
            InlineKeyboardButton("✅ قبول الطلب", callback_data=f"accept_{user.id}_{product_key}"),
            InlineKeyboardButton("❌ رفض الوصل", callback_data=f"reject_{user.id}")
        ]
    ]
    admin_markup = InlineKeyboardMarkup(admin_keyboard)

    if update.message.photo:
        await context.bot.send_photo(chat_id=ADMIN_CHAT_ID, photo=update.message.photo[-1].file_id, caption=admin_caption, reply_markup=admin_markup, parse_mode="Markdown")
    elif update.message.document:
        await context.bot.send_document(chat_id=ADMIN_CHAT_ID, document=update.message.document.file_id, caption=admin_caption, reply_markup=admin_markup, parse_mode="Markdown")

    await update.message.reply_text("⏳ تم استلام إثبات الدفع! يرجى الانتظار، سيتم الرد عليك هنا قريباً.")
    return ConversationHandler.END

async def invalid_receipt_format(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("⚠️ عذراً، يجب إرسال صورة أو ملف (PDF) للوصل.")
    return WAITING_RECEIPT

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("تم إلغاء العملية.")
    return ConversationHandler.END

# ----------------- نظام الدردشة المتبادلة (خدمة العملاء) -----------------

async def handle_customer_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    forward_text = f"📩 **رسالة من الزبون:** {user.full_name} (`{user.id}`)\n\n{update.message.text}"
    reply_markup = InlineKeyboardMarkup([[
        InlineKeyboardButton("💬 رد على الزبون", callback_data=f"reply_{user.id}")
    ]])
    await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=forward_text, reply_markup=reply_markup, parse_mode="Markdown")

async def admin_decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data.startswith("reject_"):
        customer_id = data.split("_")[1]
        try:
            await context.bot.send_message(chat_id=int(customer_id), text="❌ **عذراً!** تم رفض إثبات الدفع.\nيرجى المحاولة من جديد وإرسال وصل صحيح عبر /start.", parse_mode="Markdown")
            await query.edit_message_caption(caption=f"{query.message.caption}\n\n🛑 **تم رفض الطلب.**")
        except:
            pass

    elif data.startswith("accept_"):
        parts = data.split("_")
        customer_id = parts[1]
        
        # هذا هو السطر الذي تم إصلاحه لجمع اسم المنتج بالكامل (canva_pro)
        product_key = "_".join(parts[2:]) if len(parts) > 2 else "unknown"
        
        if product_key == "canva_pro":
            try:
                await context.bot.send_message(
                    chat_id=int(customer_id),
                    text="🎉 **تم تأكيد الدفع بنجاح!**\n\nيرجى كتابة **الإيميل الخاص بك** هنا لكي أقوم بإرسال دعوة Canva Pro إليك فوراً.",
                    parse_mode="Markdown"
                )
                await query.edit_message_caption(
                    caption=f"{query.message.caption}\n\n✅ **تم قبول الطلب.**\n🤖 (إجراء تلقائي): تم إرسال رسالة للزبون نطلب فيها إيميله.",
                    parse_mode="Markdown"
                )
            except Exception:
                await query.edit_message_caption(caption=f"{query.message.caption}\n\n❌ **خطأ:** يبدو أن الزبون حظر البوت.")
        
        else:
            context.user_data['replying_to'] = customer_id
            await query.edit_message_caption(
                caption=f"{query.message.caption}\n\n✅ **تم قبول الطلب.**\n\n👇 **أرسل الآن رسالتك للزبون (بيانات الحساب):**",
                parse_mode="Markdown"
            )

    elif data.startswith("reply_"):
        customer_id = data.split("_")[1]
        context.user_data['replying_to'] = customer_id
        await query.edit_message_text(text=f"{query.message.text}\n\n👇 **اكتب رسالتك الآن للرد على الزبون:**", parse_mode="Markdown")

async def admin_send_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'replying_to' not in context.user_data:
        return
    customer_id = context.user_data['replying_to']
    admin_text = update.message.text
    try:
        await context.bot.send_message(
            chat_id=int(customer_id),
            text=f"👨‍💻 **رسالة من الإدارة:**\n\n{admin_text}",
            parse_mode="Markdown"
        )
        await update.message.reply_text("✅ تم إرسال رسالتك للزبون بنجاح!")
        del context.user_data['replying_to']
    except Exception as e:
        await update.message.reply_text("❌ حدث خطأ، لم يتم الإرسال.")

# ----------------- نقطة التشغيل الرئيسية -----------------
def main():
    keep_alive()
    if not BOT_TOKEN:
        return
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOOSING_PRODUCT: [CallbackQueryHandler(product_selected)],
            WAITING_RECEIPT: [
                MessageHandler(filters.PHOTO | filters.Document.ALL, receive_receipt),
                MessageHandler(~(filters.PHOTO | filters.Document.ALL) & ~filters.COMMAND, invalid_receipt_format)
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(admin_decision, pattern="^(accept_|reject_|reply_)"))
    application.add_handler(MessageHandler(filters.TEXT & filters.Chat(ADMIN_CHAT_ID) & ~filters.COMMAND, admin_send_message))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.Chat(ADMIN_CHAT_ID) & ~filters.COMMAND, handle_customer_message))

    print("🤖 البوت قيد التشغيل الآن ومستعد لاستقبال الطلبات...")
    application.run_polling()

if __name__ == '__main__':
    main()
