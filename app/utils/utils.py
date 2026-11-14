# ==========================================
# ФАЙЛ app/utils/utils.py
# ==========================================
import secrets
import string
from google import genai
from google.genai import types

from config import GEMINI_API_KEY


# Примечание: Генерирует случайный инвайт-код заданной длины из букв и цифр для регистрации сотрудников.
def generate_invite_code(length: int = 8) -> str:
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


# Примечание: Проверяет надежность нового пароля (длина, пробелы, имя, телефон, последовательности, спецсимволы).
def is_strong_password(password: str, user_name: str, number: str):
    if len(password) < 12:
        return 'Пароль слишком маленький! В нём должно быть хотя бы 12 символов.'
    if ' ' in password:
        return 'В Вашем пароле есть пробелы! Их не должно быть!'
    if user_name and user_name.lower() in password.lower():
        return 'Пароль не должен содержать Ваше имя!'

    phone_digits = ''.join(filter(str.isdigit, str(number)))
    if phone_digits and phone_digits in password:
        return 'Пароль не должен содержать Ваш полный номер телефона!'

    if len(phone_digits) >= 4:
        for i in range(len(phone_digits) - 3):
            sub_number = phone_digits[i:i + 4]
            if sub_number in password:
                return f'Пароль содержит слишком длинный фрагмент Вашего телефона ({sub_number})!'

    low_password = password.lower()
    sequences = [
        'qwertyuiop', 'asdfghjkl', 'zxcvbnm',
        'йцукенгшщзхъ', 'фывапролджэё', 'ячсмитьбю',
        '01234567890', '9876543210'
    ]
    for seq in sequences:
        for i in range(len(seq) - 3):
            if seq[i:i + 4] in low_password:
                return f'Пароль содержит запрещенную последовательность символов ({seq[i:i + 4]})!'

    for i in range(len(password) - 3):
        if password[i] == password[i + 1] == password[i + 2] == password[i + 3]:
            return f'В пароле слишком много одинаковых символов подряд ({password[i] * 4})!'

    banned_words = ['password', 'admin', 'secret', 'master', 'god', 'love', 'qwerty']
    for word in banned_words:
        if word in low_password:
            return f'Пароль содержит слишком популярное и очевидное слово ({word})!'

    has_low = False
    has_up = False
    has_num = False
    has_spec = False
    special_symbols = '`!@#$%^&()-_=+[]{};,.'

    for symb in password:
        if symb.islower():
            has_low = True
        elif symb.isupper():
            has_up = True
        elif symb.isdigit():
            has_num = True
        elif symb in special_symbols:
            has_spec = True

    if not has_low:
        return 'В пароле должна быть хотя бы одна строчная буква!'
    if not has_up:
        return 'В пароле должна быть хотя бы одна заглавная буква!'
    if not has_num:
        return 'В пароле должна быть хотя бы одна цифра!'
    if not has_spec:
        return f'В пароле должен быть хотя бы один спецсимвол из набора: {special_symbols}'

    return True


# Примечание: Отправляет запрос к ИИ Gemini с контекстом тарифов, FAQ и данных абонента из БД.
async def ask_gemini_ai(user_question: str, db_context: str) -> str:
    if not GEMINI_API_KEY or GEMINI_API_KEY == "ваш_ключ_gemini_api":
        return (
            "⚠️ Ключ ИИ (GEMINI_API_KEY) еще не указан в файле .env.\n"
            "Вы можете переключиться на живого оператора кнопкой ниже."
        )

    system_instruction = (
        "Ты - вежливый, умный и лаконичный ИИ-консультант сотового оператора в Кыргызстане (валюта - сом). "
        "Отвечай на вопросы абонента четко, дружелюбно и по делу, используя актуальную информацию из базы данных ниже. "
        "Если вопрос невозможно решить без участия сотрудника, предложи нажать кнопку «Переключить на оператора».\n\n"
        f"Актуальные данные из БД:\n{db_context}"
    )

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = await client.aio.models.generate_content(
            model="gemini-3.8-flash",
            contents=user_question,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.4,
            )
        )
        return response.text or "Извините, не удалось сформировать ответ."
    except Exception as e:
        return f"⚠️ Временная ошибка связи с ИИ-помощником ({e}). Попробуйте позже или свяжитесь с оператором."
