from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy import select, delete

from database.database import get_session
from database.models import Channel, ChannelType
from config import ADMIN_IDS
from keyboards.admin import admin_panel_kb, channel_management_kb, channel_list_kb
from utils.logger import logger

router = Router()

class AdminStates(StatesGroup):
    waiting_for_mandatory = State()
    waiting_for_reward = State()

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id in ADMIN_IDS:
        await message.answer("👑 <b>Welcome to the Admin Panel!</b>", reply_markup=admin_panel_kb(), parse_mode="HTML")
    else:
        await message.answer("❌ You do not have admin privileges.")

async def safe_edit(callback: CallbackQuery, text: str, reply_markup=None):
    try:
        await callback.message.edit_text(text, reply_markup=reply_markup, parse_mode="HTML")
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            raise e

@router.callback_query(F.data == "back_to_admin")
async def back_to_admin(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS: return
    await safe_edit(callback, "👑 <b>Welcome to the Admin Panel!</b>", admin_panel_kb())

@router.callback_query(F.data == "adm_mandatory_menu")
async def adm_mandatory_menu(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS: return
    await safe_edit(callback, "📢 <b>Mandatory Channels Section</b>", channel_management_kb("mandatory"))

@router.callback_query(F.data == "adm_reward_menu")
async def adm_reward_menu(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS: return
    await safe_edit(callback, "🎁 <b>Reward Channels Section</b>", channel_management_kb("reward"))

@router.callback_query(F.data.startswith("adm_add_"))
async def adm_add_channel(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS: return
    ch_type = callback.data.split("_")[-1]
    text = "Send the following details <b>line by line</b>:\n\n1-line: Channel ID (e.g., -100xxxxxxxxx)\n2-line: Channel Name\n3-line: Username (@my_channel or leave blank)\n4-line: Invite Link (e.g., https://t.me/+Abc123 or leave blank)"
    await safe_edit(callback, text)
    if ch_type == "mandatory":
        await state.set_state(AdminStates.waiting_for_mandatory)
    else:
        await state.set_state(AdminStates.waiting_for_reward)

@router.message(AdminStates.waiting_for_mandatory)
@router.message(AdminStates.waiting_for_reward)
async def process_add_channel(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    lines = message.text.strip().split('\n')
    if len(lines) < 2:
        await message.answer("❌ Invalid format. Please fill at least lines 1 and 2.", reply_markup=admin_panel_kb())
        await state.clear()
        return

    channel_id_str = lines[0].strip()
    title = lines[1].strip()
    username = lines[2].strip() if len(lines) > 2 else None
    invite_link = lines[3].strip() if len(lines) > 3 else ""

    try:
        channel_id = int(channel_id_str)
    except ValueError:
        await message.answer("❌ Channel ID must be a number.", reply_markup=admin_panel_kb())
        await state.clear()
        return

    ch_type = ChannelType.MANDATORY if await state.get_state() == "AdminStates:waiting_for_mandatory" else ChannelType.REWARD
    await state.clear()
    
    async for session in get_session():
        try:
            new_channel = Channel(channel_id=channel_id, title=title, username=username, invite_link=invite_link, channel_type=ch_type)
            session.add(new_channel)
            await session.commit()
            await message.answer(f"✅ Channel <b>{title}</b> added successfully!", reply_markup=admin_panel_kb(), parse_mode="HTML")
        except Exception as e:
            logger.error(f"Error adding channel: {e}")
            await message.answer(f"❌ Error (This ID might already exist).", reply_markup=admin_panel_kb())

@router.callback_query(F.data.startswith("adm_list_"))
async def adm_list_channels(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS: return
    ch_type_str = callback.data.split("_")[-1]
    ch_type = ChannelType.MANDATORY if ch_type_str == "mandatory" else ChannelType.REWARD
    async for session in get_session():
        stmt = select(Channel).where(Channel.channel_type == ch_type)
        result = await session.execute(stmt)
        channels = result.scalars().all()
        
    if not channels:
        await safe_edit(callback, "ℹ️ No channels found.", channel_management_kb(ch_type_str))
    else:
        await safe_edit(callback, f"📋 <b>{ch_type_str.capitalize()} Channels List:</b>\n\nSelect a channel to delete:", channel_list_kb(channels, ch_type_str))

@router.callback_query(F.data.startswith("adm_del_"))
async def adm_del_channel(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS: return
    parts = callback.data.split("_")
    ch_type_str = parts[2]
    ch_type = ChannelType.MANDATORY if ch_type_str == "mandatory" else ChannelType.REWARD
    channel_id = int(parts[3])
    
    async for session in get_session():
        stmt = delete(Channel).where(Channel.id == channel_id)
        await session.execute(stmt)
        await session.commit()
        
    await callback.answer("Channel deleted!", show_alert=True)
    
    async for session in get_session():
        stmt = select(Channel).where(Channel.channel_type == ch_type)
        result = await session.execute(stmt)
        channels = result.scalars().all()
        
    if not channels:
        await safe_edit(callback, "✅ Channel deleted.\n\nℹ️ No more channels left.", channel_management_kb(ch_type_str))
    else:
        await safe_edit(callback, f"✅ Channel deleted.\n\n📋 <b>{ch_type_str.capitalize()} Channels List:</b>", channel_list_kb(channels, ch_type_str))