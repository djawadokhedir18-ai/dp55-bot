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

# ----------------- دوال الزبون -----------------

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
    context.user_data['price'] = product['price']

    message_text = (
        f"✅ لقد اخترت: **{product['name']}**\n"
        f"💰 المبلغ المطلوب: **{product['price']}**\n\n"
        f"{PAYMENT_DETAILS}"
    )

    await query.edit_message_text(text=message_text, parse_mode="Markdown")
    return WAITING_RECEIPT

async def receive_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """إرسال التنبيه للأدمن مع أزرار التحكم (قبول/رفض)"""
    user = update.effective_user
    product_name = context.user_data.get('selected_product', 'منتج غير محدد')
    price = context.user_data.get('price', '')

    admin_caption = (
        "🚨 **طلب شراء جديد!**\n\n"
        f"👤 الزبون: {user.full_name}\n"
        f"🆔 معرف الزبون: `{user.id}`\n"
        f"📦 المنتج: **{product_name}** ({price})\n\n"
        "إثبات الدفع مرفق 👆. يرجى اختيار الإجراء المناسب:"
    )

    # أزرار تحكم خاصة بك كأدمن
    admin_keyboard = [
        [
            InlineKeyboardButton("✅ قبول (تسليم الاشتراك)", callback_data=f"accept_{user.id}_{product_name}"),
            InlineKeyboardButton("❌ رفض الوصل", callback_data=f"reject_{user.id}")
        ]
    ]
    admin_markup = InlineKeyboardMarkup(admin_keyboard)

    # إرسال الصورة أو الملف مع الأزرار لك
    if update.message.photo:
        await context.bot.send_photo(
            chat_id=ADMIN_CHAT_ID,
            photo=update.message.photo[-1].file_id,
            caption=admin_caption,
            reply_markup=admin_markup,
            parse_mode="Markdown"
        )
    elif update.message.document:
        await context.bot.send_document(
            chat_id=ADMIN_CHAT_ID,
            document=update.message.document.file_id,
            caption=admin_caption,
            reply_markup=admin_markup,
            parse_mode="Markdown"
        )

    await update.message.reply_text(
        "⏳ تم استلام إثبات الدفع بنجاح!\n"
        "طلبك الآن قيد المراجعة، يرجى الانتظار هنا، سنرسل لك بيانات الاشتراك في هذه المحادثة قريباً جداً."
    )
    return ConversationHandler.END

async def invalid_receipt_format(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("⚠️ عذراً، يجب إرسال صورة أو ملف (PDF) للوصل.")
    return WAITING_RECEIPT

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("تم إلغاء العملية.")
    return ConversationHandler.END

# ----------------- دوال الإدارة (خاصة بك) -----------------

async def admin_decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """التعامل مع ضغطات الأدمن (أنت) على أزرار القبول أو الرفض"""
    query = update.callback_query
    await query.answer()

    data = query.data
    
    # إذا ضغطت "رفض"
    if data.startswith("reject_"):
        customer_id = data.split("_")[1]
        
        # إرسال رسالة للزبون
        try:
            await context.bot.send_message(
                chat_id=int(customer_id),
                text="❌ **عذراً!** تم رفض إثبات الدفع الخاص بك (الوصل غير واضح أو غير صحيح).\nيرجى المحاولة من جديد وإرسال وصل صحيح عبر /start.",
                parse_mode="Markdown"
            )
            # تعديل رسالتك أنت لتعرف أنك رفضته
            await query.edit_message_caption(caption=f"{query.message.caption}\n\n🛑 **تم رفض الطلب وإبلاغ الزبون.**")
        except Exception as e:
            await query.edit_message_caption(caption="حدث خطأ! الزبون ربما حظر البوت.")

    # إذا ضغطت "قبول"
    elif data.startswith("accept_"):
        parts = data.split("_")
        customer_id = parts[1]
        product_name = "_".join(parts[2:]) # استخراج اسم المنتج
        
        # نضع الزبون في "قائمة الانتظار" لكي ترد عليه
        context.user_data['replying_to'] = customer_id
        
        await query.edit_message_caption(
            caption=f"{query.message.caption}\n\n✅ **تم قبول الطلب.**\n\n👇 **أرسل الآن رسالة نصية تحتوي على (الإيميل وكلمة السر) الخاصين بـ {product_name} ليتم تسليمها للزبون فوراً.**",
            parse_mode="Markdown"
        )

async def admin_send_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هذه الدالة تأخذ النص الذي ستكتبه أنت و ترسله للزبون كبيانات اشتراك"""
    # التحقق من أن الرسالة من الأدمن وأنه اختار "قبول"
    if update.effective_chat.id != ADMIN_CHAT_ID or 'replying_to' not in context.user_data:
        return

    customer_id = context.user_data['replying_to']
    subscription_details = update.message.text

    try:
        # إرسال بيانات الاشتراك للزبون
        await context.bot.send_message(
            chat_id=int(customer_id),
            text=f"🎉 **تم تأكيد الدفع بنجاح!**\n\nإليك بيانات الاشتراك الخاصة بك:\n\n`{subscription_details}`\n\nنشكرك على ثقتك بمتجرنا!",
            parse_mode="Markdown"
        )
        
        # تأكيد لك أن الرسالة وصلت
        await update.message.reply_text("✅ تم إرسال بيانات الاشتراك للزبون بنجاح!")
        
        # تنظيف الذاكرة لكي لا يرسل رسائل بالخطأ لاحقاً
        del context.user_data['replying_to']

    except Exception as e:
        await update.message.reply_text("❌ حدث خطأ، لم يتم الإرسال. قد يكون الزبون قد أوقف البوت.")

# ----------------- نقطة التشغيل الرئيسية -----------------
def main():
    keep_alive()

    if not BOT_TOKEN:
        return

    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # محادثة الزبون
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
    
    # التعامل مع أزرار الأدمن (قبول/رفض)
    application.add_handler(CallbackQueryHandler(admin_decision, pattern="^(accept_|reject_)"))
    
    # التعامل مع رسالة تسليم الاشتراك من الأدمن
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_send_subscription))

    print("🤖 البوت قيد التشغيل الآن ومستعد لاستقبال الطلبات...")
    application.run_polling()

if __name__ == '__main__':
    main()
