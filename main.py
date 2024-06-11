from aiogram import Bot, Dispatcher, types, executor
from aiogram.dispatcher.filters.builtin import CommandStart
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

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


@dp.message_handler(CommandStart())
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    if is_registered(user_id):
        await message.answer("Привет) Ты уже зарегистрирован) Вход выполнен успешно!)")
    else:
        await message.answer(
            "Привет! Я бот для сбора баллов ЕГЭ. Ты можешь зарегистрироваться с помощью команды /register.")


@dp.message_handler(commands=['register'])
async def cmd_register(message: types.Message):
    user_id = message.from_user.id
    if is_registered(user_id):
        await message.answer("Ты уже зарегистрирован)")
    else:
        await message.answer("Введите ваше имя:")
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


@dp.message_handler(commands=['enter_scores'])
async def cmd_enter_scores(message: types.Message):
    await message.answer("Введи название предмета:")
    await ScoreForm.subject.set()


@dp.message_handler(state=ScoreForm.subject)
async def process_subject(message: types.Message, state: FSMContext):
    subject = message.text.strip()
    if not is_valid_subject(subject):
        await message.answer("Пожалуйста, введите корректное название предмета (только буквы и пробелы).")
        return
    else:
        await state.update_data(subject=message.text)
        await message.answer("Введите полученный балл:")
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
    else:
        await message.answer("Пожалуйста, введи верное числовое значение для балла.")


@dp.message_handler(commands=['view_scores'])
async def cmd_view_scores(message: types.Message):
    user_id = message.from_user.id
    scores = get_scores(user_id)
    if scores:
        response = "Твои баллы ЕГЭ:\n"
        response += "\n".join([f"{subject}: {score}" for subject, score in scores])
    else:
        response = "У тебя нет сохраненных баллов("
    await message.answer(response)


if __name__ == '__main__':
    init_db()
    executor.start_polling(dp, skip_updates=True)
