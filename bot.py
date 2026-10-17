import asyncio
import logging
import random
import sqlite3
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery

API_TOKEN = '8967573172:AAHLKIh8VIjLr7XNS9VUA4QBfspQs8PyDR4'

def init_db():
    conn = sqlite3.connect('words.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS words (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            en TEXT,
            ru TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)

class AddWordStates(StatesGroup):
    waiting_for_en = State()
    waiting_for_ru = State()

def get_main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить слово", callback_data="add_word")],
        [InlineKeyboardButton(text="🇬🇧➡️🇷🇺 Тренировать (EN -> RU)", callback_data="train_en_ru")],
        [InlineKeyboardButton(text="🇷🇺➡️🇬🇧 Тренировать (RU -> EN)", callback_data="train_ru_en")],
        [InlineKeyboardButton(text="📚 Мои слова", callback_data="list_words")]
    ])

@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "Привет! Я твой личный бот для изучения английских слов.\nВыбери действие:",
        reply_markup=get_main_keyboard()
    )

@router.callback_query(F.data == "add_word")
async def add_word_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Напиши английское слово (или фразу), которое хочешь добавить:")
    await state.set_state(AddWordStates.waiting_for_en)
    await callback.answer()

@router.message(AddWordStates.waiting_for_en)
async def process_en_word(message: Message, state: FSMContext):
    await state.update_data(en_word=message.text)
    await message.answer("Теперь отправь перевод (на русский или украинский):")
    await state.set_state(AddWordStates.waiting_for_ru)

@router.message(AddWordStates.waiting_for_ru)
async def process_ru_word(message: Message, state: FSMContext):
    data = await state.get_data()
    en_word = data['en_word']
    ru_word = message.text
    user_id = message.from_user.id

    conn = sqlite3.connect('words.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO words (user_id, en, ru) VALUES (?, ?, ?)', (user_id, en_word, ru_word))
    conn.commit()
    conn.close()

    await state.clear()
    await message.answer(
        f"✅ Успешно добавлено!\nEnglish: {en_word}\nПеревод: {ru_word}",
        reply_markup=get_main_keyboard()
    )

@router.callback_query(F.data == "train_en_ru")
async def train_en_ru(callback: CallbackQuery):
    user_id = callback.from_user.id
    conn = sqlite3.connect('words.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, en, ru FROM words WHERE user_id = ?', (user_id,))
    words = cursor.fetchall()
    conn.close()

    if not words:
        await callback.message.answer("У тебя пока нет сохраненных слов. Сначала добавь их!", reply_markup=get_main_keyboard())
        await callback.answer()
        return

    word = random.choice(words)
    word_id, en, ru = word[0], word[1], word[2]

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👁 Показать перевод", callback_data=f"show_ru_{word_id}")],
        [InlineKeyboardButton(text="➡️ Следующее слово", callback_data="train_en_ru")],
        [InlineKeyboardButton(text="🏠 В меню", callback_data="main_menu")]
    ])

    await callback.message.edit_text(f"Как переводится слово:\n\n<b>{en}</b>", parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data.startswith("show_ru_"))
async def show_ru_translation(callback: CallbackQuery):
    word_id = int(callback.data.split("_")[2])
    conn = sqlite3.connect('words.db')
    cursor = conn.cursor()
    cursor.execute('SELECT en, ru FROM words WHERE id = ?', (word_id,))
    word = cursor.fetchone()
    conn.close()

    if word:
        en, ru = word[0], word[1]
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➡️ Следующее слово", callback_data="train_en_ru")],
            [InlineKeyboardButton(text="🏠 В меню", callback_data="main_menu")]
        ])
        await callback.message.edit_text(f"Слово: <b>{en}</b>\nПеревод: <b>{ru}</b>", parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data == "train_ru_en")
async def train_ru_en(callback: CallbackQuery):
    user_id = callback.from_user.id
    conn = sqlite3.connect('words.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, en, ru FROM words WHERE user_id = ?', (user_id,))
    words = cursor.fetchall()
    conn.close()

    if not words:
        await callback.message.answer("У тебя пока нет сохраненных слов. Сначала добавь их!", reply_markup=get_main_keyboard())
        await callback.answer()
        return

    word = random.choice(words)
    word_id, en, ru = word[0], word[1], word[2]

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👁 Показать английский", callback_data=f"show_en_{word_id}")],
        [InlineKeyboardButton(text="➡️ Следующее слово", callback_data="train_ru_en")],
        [InlineKeyboardButton(text="🏠 В меню", callback_data="main_menu")]
    ])

    await callback.message.edit_text(f"Как переводится на английский:\n\n<b>{ru}</b>", parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data.startswith("show_en_"))
async def show_en_translation(callback: CallbackQuery):
    word_id = int(callback.data.split("_")[2])
    conn = sqlite3.connect('words.db')
    cursor = conn.cursor()
    cursor.execute('SELECT en, ru FROM words WHERE id = ?', (word_id,))
    word = cursor.fetchone()
    conn.close()

    if word:
        en, ru = word[0], word[1]
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➡️ Следующее слово", callback_data="train_ru_en")],
            [InlineKeyboardButton(text="🏠 В меню", callback_data="main_menu")]
        ])
        await callback.message.edit_text(f"Перевод: <b>{ru}</b>\nПо-английски: <b>{en}</b>", parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data == "main_menu")
async def back_to_menu(callback: CallbackQuery):
    await callback.message.edit_text("Главное меню:", reply_markup=get_main_keyboard())
    await callback.answer()

@router.callback_query(F.data == "list_words")
async def list_words(callback: CallbackQuery):
    user_id = callback.from_user.id
    conn = sqlite3.connect('words.db')
    cursor = conn.cursor()
    cursor.execute('SELECT en, ru FROM words WHERE user_id = ?', (user_id,))
    words = cursor.fetchall()
    conn.close()

    if not words:
        await callback.message.answer("Список слов пуст.", reply_markup=get_main_keyboard())
    else:
        text = "<b>Твои слова:</b>\n\n" + "\n".join([f"• {w[0]} — {w[1]}" for w in words])
        if len(text) > 4096:
            text = text[:4096]
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 В меню", callback_data="main_menu")]
        ])
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
