from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def main_menu_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👤 My Profile")],
            [KeyboardButton(text="📊 My Referrals")],
            [KeyboardButton(text="🎁 Claim Reward")]
        ],
        resize_keyboard=True
    )

def back_to_main_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔙 Back")]
        ],
        resize_keyboard=True
    )