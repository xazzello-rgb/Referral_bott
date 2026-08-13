from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart
from aiogram.exceptions import TelegramBadRequest
from keyboards.user import main_menu_kb
from utils.helpers import build_channel_buttons
from services.subscriptions import get_unsubscribed_mandatory_channels
from services.referrals import process_referral
from database.database import get_session
from database import queries
from config import ADMIN_IDS
from utils.logger import logger

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, bot):
    user_id = message.from_user.id
    args = message.text.split()
    referrer_id = None

    if len(args) > 1:
        arg = args[1]
        try:
            referrer_id = int(arg)
        except ValueError:
            pass

    async for session in get_session():
        user = await queries.get_user_by_telegram_id(session, user_id)
        if not user:
            can_add = True
            if referrer_id:
                can_add = await process_referral(user_id, referrer_id)
            
            await queries.add_user(
                session=session,
                telegram_id=user_id,
                username=message.from_user.username,
                full_name=message.from_user.first_name,
                referred_by=referrer_id if can_add and referrer_id else None
            )
            logger.info(f"New user: {user_id} (Referrer: {referrer_id})")

    unsubscribed = await get_unsubscribed_mandatory_channels(bot, user_id)
    
    if unsubscribed:
        text = "📢 To use the bot, please join the following channels:"
        kb = build_channel_buttons(unsubscribed, "check_sub_again")
        await message.answer(text, reply_markup=kb)
    else:
        if user_id in ADMIN_IDS:
            from keyboards.admin import admin_panel_kb
            await message.answer("👑 Welcome to the Admin Panel!", reply_markup=admin_panel_kb())
        
        bot_info = await bot.get_me()
        referral_link = f"https://t.me/{bot_info.username}?start={user_id}"
        
        promo_text = (
            "⚡️ Join the SAT MARATHON and learn how to ace the SAT Math section! 🚀\n\n"
            "📚 Your teachers will be:\n\n"
            "👨‍🏫 Mr. Yoqubjon\n"
            "👨‍🏫 Mr. Xasanbek\n"
            "👨‍🏫 Mr. Xuzayfa\n\n"
            "🎯 Learn effective strategies and techniques to achieve a high score in SAT Math!\n\n"
            "🔐 To get access to the private channel, invite 3 of your friends using the referral link below.\n\n"
            f"🔗 <b>Your Referral Link:</b>\n<code>{referral_link}</code>\n\n"
            "Invite your friends and join the SAT MARATHON! 🔥"
        )
        
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="👤 My Profile")],
                [KeyboardButton(text="📊 My Referrals")],
                [KeyboardButton(text="🎁 Claim Reward")]
            ],
            resize_keyboard=True
        )
        
        await message.answer(promo_text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "check_sub_again")
async def check_sub_again(callback: CallbackQuery, bot):
    await callback.answer()
    user_id = callback.from_user.id
    unsubscribed = await get_unsubscribed_mandatory_channels(bot, user_id)
    
    if unsubscribed:
        text = "❌ You haven't joined all channels yet!\n\nPlease subscribe to all channels:"
        kb = build_channel_buttons(unsubscribed, "check_sub_again")
        try:
            await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                raise e
    else:
        bot_info = await bot.get_me()
        referral_link = f"https://t.me/{bot_info.username}?start={user_id}"
        
        promo_text = (
            "✅ Verified!\n\n"
            "⚡️ Join the SAT MARATHON and learn how to ace the SAT Math section! 🚀\n\n"
            "📚 Your teachers will be:\n\n"
            "👨‍🏫 Mr. Yoqubjon\n"
            "👨‍🏫 Mr. Xasanbek\n"
            "👨‍🏫 Mr. Xuzayfa\n\n"
            "🎯 Learn effective strategies and techniques to achieve a high score in SAT Math!\n\n"
            "🔐 To get access to the private channel, invite 3 of your friends using the referral link below.\n\n"
            f"🔗 <b>Your Referral Link:</b>\n<code>{referral_link}</code>\n\n"
            "Invite your friends and join the SAT MARATHON! 🔥"
        )
        
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="👤 My Profile")],
                [KeyboardButton(text="📊 My Referrals")],
                [KeyboardButton(text="🎁 Claim Reward")]
            ],
            resize_keyboard=True
        )
        
        try:
            await callback.message.edit_text(promo_text, reply_markup=kb, parse_mode="HTML")
        except TelegramBadRequest:
            await callback.message.answer(promo_text, reply_markup=kb, parse_mode="HTML")
            
        if user_id in ADMIN_IDS:
            from keyboards.admin import admin_panel_kb
            await callback.message.answer("👑 Welcome to the Admin Panel!", reply_markup=admin_panel_kb())