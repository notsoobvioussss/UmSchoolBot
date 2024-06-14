from aiogram import Bot, Dispatcher, types, executor
from aiogram.dispatcher.filters.builtin import CommandStart
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

import config
from database import init_db, register_student, enter_score, get_scores, is_registered
import re

API_TOKEN = config.API_TOKEN

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())


class RegisterForm(StatesGroup):
    first_name = State()
    last_name = State()


class ScoreForm(StatesGroup):
    subject = State()
    score = State()


def is_valid_name(name):
    return re.match(r'^[A-Za-zА-Яа-яЁё]+$', name)


def is_valid_subject(subject):
    return re.match(r'^[A-Za-zА-Яа-яЁё\s]+$', subject) is not None

async def kb_action() -> ReplyKeyboardMarkup:
    scores_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    scores_button = KeyboardButton("Ввод баллов")
    view_scores_button = KeyboardButton("Просмотр баллов")
    scores_keyboard.add(scores_button, view_scores_button)
    return scores_keyboard


@dp.message_handler(CommandStart())
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    if is_registered(user_id):
        await message.answer("Привет) Ты уже зарегистрирован) Вход выполнен успешно!)")
        await message.answer("Выберите действие:", reply_markup=await kb_action())
    else:
        register_button = InlineKeyboardButton("Зарегистрироваться", callback_data="register")
        register_keyboard = InlineKeyboardMarkup().add(register_button)
        await message.answer(
            "Привет! Я бот для сбора баллов ЕГЭ. Ты можешь зарегистрироваться с помощью кнопки ниже.",
            reply_markup=register_keyboard
        )


@dp.callback_query_handler(lambda c: c.data == 'register')
async def process_callback_register(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    message = callback_query.message
    message.text = "/register"
    message.from_user = callback_query.from_user
    await cmd_register(message)


@dp.message_handler(lambda message: message.text == "Ввод баллов")
async def handle_enter_scores(message: types.Message):
    user_id = message.from_user.id
    if is_registered(user_id):
        await cmd_enter_scores(message)
    else:
        register_button = InlineKeyboardButton("Зарегистрироваться", callback_data="register")
        register_keyboard = InlineKeyboardMarkup().add(register_button)
        await message.answer(
            "Для ввода баллов необходимо зарегистрироваться.",
            reply_markup=register_keyboard
        )
        await message.answer("Выберите действие:", reply_markup=await kb_action())


@dp.message_handler(lambda message: message.text == "Просмотр баллов")
async def handle_view_scores(message: types.Message):
    user_id = message.from_user.id
    if is_registered(user_id):
        await cmd_view_scores(message)
    else:
        register_button = InlineKeyboardButton("Зарегистрироваться", callback_data="register")
        register_keyboard = InlineKeyboardMarkup().add(register_button)
        await message.answer(
            "Для просмотра баллов необходимо зарегистрироваться.",
            reply_markup=register_keyboard
        )
        await message.answer("Выберите действие:", reply_markup=await kb_action())


@dp.message_handler(commands=['register'])
async def cmd_register(message: types.Message):
    user_id = message.from_user.id
    if is_registered(user_id):
        await message.answer("Ты уже зарегистрирован)")
    else:
        await message.answer("Введите ваше имя:", reply_markup=types.ReplyKeyboardRemove())
        await RegisterForm.first_name.set()


@dp.message_handler(state=RegisterForm.first_name)
async def process_first_name(message: types.Message, state: FSMContext):
    if not is_valid_name(message.text.strip()):
        await message.answer("Имя не может содержать специальные символы или цифры. Пожалуйста, введи свое имя снова:")
        return
    await state.update_data(first_name=message.text)
    await message.answer("Введи свою фамилию:")
    await RegisterForm.next()


@dp.message_handler(state=RegisterForm.last_name)
async def process_last_name(message: types.Message, state: FSMContext):
    if not is_valid_name(message.text.strip()):
        await message.answer(
            "Фамилия не может содержать специальные символы или цифры. Пожалуйста, введите свою фамилию снова:")
        return
    data = await state.get_data()
    user_id = message.from_user.id
    first_name = data['first_name']
    last_name = message.text
    register_student(user_id, first_name, last_name)
    await state.finish()
    await message.answer("Ты успешно зарегистрирован!")
    await message.answer("Выберите действие:", reply_markup=await kb_action())


@dp.message_handler(commands=['enter_scores'])
async def cmd_enter_scores(message: types.Message):
    subjects_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    subjects = ["Математика профильная", "Информатика", "Обществознание", "Русский язык"]
    subjects_keyboard.add(*subjects)
    await message.answer("Введи название предмета:", reply_markup=subjects_keyboard)
    await ScoreForm.subject.set()


@dp.message_handler(state=ScoreForm.subject)
async def process_subject(message: types.Message, state: FSMContext):
    subject = message.text.strip()
    user_id = message.from_user.id
    existing_scores = get_scores(user_id)
    if not is_valid_subject(subject):
        await message.answer("Пожалуйста, введите корректное название предмета (только буквы и пробелы).")
        return
    if any(score["subject"] == subject for score in existing_scores):
        await message.answer("Этот предмет уже добавлен. Пожалуйста, введите другой предмет.")
        return
    await state.update_data(subject=subject)
    await message.answer("Введите полученный балл:", reply_markup=types.ReplyKeyboardRemove())
    await ScoreForm.next()


@dp.message_handler(state=ScoreForm.score)
async def process_score(message: types.Message, state: FSMContext):
    try:
        score = int(message.text)
    except ValueError:
        await message.answer("Пожалуйста, введи числовое значение для балла.")
        return
    if 0 <= score <= 100:
        data = await state.get_data()
        user_id = message.from_user.id
        subject = data['subject']
        enter_score(user_id, subject, score)
        await state.finish()
        await message.answer("Балл успешно сохранен!")
        await message.answer("Выберите действие:", reply_markup=await kb_action())
    else:
        await message.answer("Пожалуйста, введи верное числовое значение для балла.")


@dp.message_handler(commands=['view_scores'])
async def cmd_view_scores(message: types.Message):
    user_id = message.from_user.id
    scores = get_scores(user_id)
    if scores:
        response = "Твои баллы ЕГЭ:\n"
        response += "\n".join([f"{i['subject']}: {i['score']}" for i in scores])
    else:
        response = "У тебя нет сохраненных баллов("
    await message.answer(response, reply_markup=await kb_action())


if __name__ == '__main__':
    init_db()
    executor.start_polling(dp, skip_updates=True)
