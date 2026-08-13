from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy import select, func

from keyboards.user import main_menu_kb
from utils.helpers import build_channel_buttons
from services.subscriptions import get_unsubscribed_mandatory_channels
from database.database import get_session
from database import queries
from database.models import Channel, ChannelType, RewardLink, User
from config import REQUIRED_REFERRALS

router = Router()

@router.message(F.text == "👤 My Profile")
async def show_profile(message: Message):
    user_id = message.from_user.id
    user = None
    async for session in get_session():
        user = await queries.get_user_by_telegram_id(session, user_id)
    
    if user:
        name = user.full_name or "Not specified"
        username = user.username or "None"
        text = f"👤 <b>Your Profile</b>\n\n🆔 ID: <code>{user.telegram_id}</code>\n📛 Name: {name}\n🌐 Username: @{username}"
    else:
        text = "❌ User not found."
    await message.answer(text, parse_mode="HTML")

@router.message(F.text == "📊 My Referrals")
async def show_stats(message: Message):
    user_id = message.from_user.id
    count = 0
    async for session in get_session():
        stmt = select(func.count()).where(User.referred_by == user_id)
        result = await session.execute(stmt)
        count = result.scalar() or 0
        
    text = f"📊 <b>Statistics</b>\n\nTotal Invites: <b>{count}</b>\nRequired: <b>{REQUIRED_REFERRALS}</b>\nRemaining: <b>{max(0, REQUIRED_REFERRALS - count)}</b>"
    await message.answer(text, parse_mode="HTML")

@router.message(F.text == "🎁 Claim Reward")
async def show_reward(message: Message, bot: Bot):
    user_id = message.from_user.id
    
    count = 0
    async for session in get_session():
        stmt = select(func.count()).where(User.referred_by == user_id)
        result = await session.execute(stmt)
        count = result.scalar() or 0

    if count < REQUIRED_REFERRALS:
        text = f"🎁 <b>Reward</b>\n\nYou need <b>{max(0, REQUIRED_REFERRALS - count)}</b> more friends.\nInvite your friends using your referral link!"
        await message.answer(text, parse_mode="HTML")
        return

    async for session in get_session():
        stmt_check = select(RewardLink).where(RewardLink.user_id == user_id)
        res_check = await session.execute(stmt_check)
        existing_link = res_check.scalar_one_or_none()

        stmt_ch = select(Channel).where(Channel.channel_type == ChannelType.REWARD).first()
        res_ch = await session.execute(stmt_ch)
        reward_channel = res_ch.scalar_one_or_none()

        if not reward_channel:
            text = "❌ There are no reward channels available right now."
            await message.answer(text, parse_mode="HTML")
            return

        generated_link = None
        if existing_link:
            generated_link = existing_link.token

        if not generated_link:
            try:
                chat_invite = await bot.create_chat_invite_link(
                    chat_id=reward_channel.channel_id,
                    member_limit=1, 
                    name=f"Reward for {user_id}" 
                )
                generated_link = chat_invite.invite_link
                
                new_link = RewardLink(token=generated_link, channel_id=reward_channel.id, user_id=0)
                session.add(new_link)
                await session.flush() 
                new_link.user_id = user_id
                await session.commit()
            except TelegramBadRequest as e:
                await message.answer("❌ Error creating link: The bot is not an admin in this channel!", parse_mode="HTML")
                return

        await message.answer(
            f"🎉 <b>Congratulations!</b> You have invited {REQUIRED_REFERRALS} friends!\n\n"
            f"🎁 <b>Your exclusive 1-time link:</b>\n\n"
            f"{generated_link}\n\n"
            f"⚠️ Click on it to join the channel!",
            parse_mode="HTML"
        )

async def safe_edit(callback: CallbackQuery, text: str, reply_markup=None):
    try:
        await callback.message.edit_text(text, reply_markup=reply_markup, parse_mode="HTML")
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            raise e

@router.callback_query(F.data == "menu_channels")
async def show_channels(callback: CallbackQuery, bot: Bot):
    await callback.answer()
    unsubscribed = await get_unsubscribed_mandatory_channels(bot, callback.from_user.id)
    if unsubscribed:
        text = "📢 <b>Mandatory Channels</b>\n\nPlease subscribe:"
        kb = build_channel_buttons(unsubscribed, "check_sub_from_menu")
        await safe_edit(callback, text, reply_markup=kb)
    else:
        text = "✅ You are subscribed to all channels!"
        await safe_edit(callback, text, reply_markup=main_menu_kb())

@router.callback_query(F.data == "check_sub_from_menu")
async def check_sub_from_menu(callback: CallbackQuery, bot: Bot):
    from handlers.start import check_sub_again
    await check_sub_again(callback, bot)

@router.callback_query(F.data == "no_link")
async def no_link_warning(callback: CallbackQuery):
    await callback.answer("⚠️ No link provided for this channel by admin!", show_alert=True)

@router.callback_query(F.data == "menu_help")
async def show_help(callback: CallbackQuery):
    await callback.answer()
    text = "❓ <b>Help</b>\n\n1. Subscribe to the channels.\n2. Share your link with friends.\n3. Reach the required amount to get the reward."
    await safe_edit(callback, text, reply_markup=main_menu_kb())

@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    await callback.answer()
    text = "Welcome to the bot!\n\nPlease choose an option from the menu below:"
    await safe_edit(callback, text, reply_markup=main_menu_kb())