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
# هذا السطر مهم جداً لربط ملف keep_alive وتشغيل البوت 24/7
from keep_alive import keep_alive

# إعداد السجلات لمتابعة الأخطاء
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
    "📌 بعد إتمام الدفع، يرجى **إرسال صورة الوصل (Reçu) هنا مباشرة** ليتم معالجة طلبك وتسليمك الاشتراك فوراً."
)

PRODUCTS = {
    "gemini_pro": {"name": "اشتراك Gemini Pro", "price": "700 دج"},
    "canva_pro": {"name": "اشتراك Canva Pro (سنة)", "price": "400 دج"},
    "chatgpt_plus": {"name": "اشتراك ChatGPT Plus", "price": "2000 دج"},
}

CHOOSING_PRODUCT, WAITING_RECEIPT = range(2)

# ----------------- دوال البوت -----------------

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
    """استقبال صورة الوصل وإرسال التنبيه للأدمن"""
    user = update.effective_user
    product_name = context.user_data.get('selected_product', 'منتج غير محدد')
    price = context.user_data.get('price', '')

    photo_file_id = update.message.photo[-1].file_id

    admin_caption = (
        "🚨 **طلب شراء جديد وارد!**\n\n"
        f"👤 الزبون: {user.full_name} (@{user.username if user.username else 'لا يوجد معرف'})\n"
        f"🆔 معرف الزبون: `{user.id}`\n"
        f"📦 المنتج: **{product_name}** ({price})\n\n"
        "📄 صورة الوصل مرفقة أدناه للتأكد من الدفع:"
    )

    await context.bot.send_photo(
        chat_id=ADMIN_CHAT_ID,
        photo=photo_file_id,
        caption=admin_caption,
        parse_mode="Markdown"
    )

    await update.message.reply_text(
        "✅ تم استلام إيصال الدفع بنجاح!\n"
        "يتم الآن التحقق من المعاملة وسنقوم بإرسال بيانات الاشتراك إليك هنا في أقرب وقت."
    )
    return ConversationHandler.END

async def invalid_receipt_format(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """هذه الدالة تعمل إذا أرسل الزبون نصاً بدلاً من صورة الوصل"""
    await update.message.reply_text(
        "⚠️ عذراً، يجب إرسال **صورة** واضحة لوصل الدفع (Reçu) وليس رسالة نصية.\n\n"
        "يرجى تصوير الوصل وإرساله هنا لكي نتمكن من تأكيد طلبك.",
        parse_mode="Markdown"
    )
    return WAITING_RECEIPT

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("تم إلغاء العملية. يمكنك البدء من جديد عبر إرسال /start.")
    return ConversationHandler.END

# ----------------- نقطة التشغيل الرئيسية -----------------
def main():
    # تشغيل الخادم الوهمي لإبقاء البوت مستيقظاً
    keep_alive()

    if not BOT_TOKEN:
        print("❌ خطأ: التوكن غير موجود! تأكد من إضافته في المتغيرات البيئية (Environment Variables).")
        return

    application = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOOSING_PRODUCT: [CallbackQueryHandler(product_selected)],
            WAITING_RECEIPT: [
                MessageHandler(filters.PHOTO, receive_receipt),
                MessageHandler(~filters.PHOTO & ~filters.COMMAND, invalid_receipt_format)
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(conv_handler)

    print("🤖 البوت قيد التشغيل الآن ومستعد لاستقبال الطلبات...")
    application.run_polling()

if __name__ == '__main__':
    main()
