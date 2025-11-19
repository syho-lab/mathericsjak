import os
import logging
import asyncio
import requests
from datetime import datetime
from flask import Flask
from threading import Thread

import sympy as sp
from sympy import pretty, symbols, solve, integrate, diff, limit, simplify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Глобальные переменные
USER_HISTORY = {}
app = Flask(__name__)

class MathBot:
    def __init__(self, token):
        self.token = token
        self.app = Application.builder().token(token).build()
        self.setup_handlers()
    
    def setup_handlers(self):
        """Настройка обработчиков"""
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        self.app.add_handler(CallbackQueryHandler(self.button_handler))
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user = update.effective_user
        keyboard = [
            [InlineKeyboardButton("🧮 Решить пример", callback_data="solve_example")],
            [InlineKeyboardButton("❓ Помощь", callback_data="help")],
            [InlineKeyboardButton("📚 История решений", callback_data="history")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        welcome_text = f"""
✨ *Добро пожаловать, {user.first_name}!* ✨

🤖 Я — продвинутый математический бот, который поможет решить *любые* математические примеры:

🔢 *Арифметические операции*
📐 *Алгебраические выражения* 
📈 *Производные и интегралы*
∞ *Пределы и ряды*
⚡ *Сложные математические задачи*

Просто отправьте мне математический пример, и я решу его поэтапно с подробными объяснениями! 🎯
        """
        
        await update.message.reply_text(
            welcome_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        help_text = """
📖 *Справка по использованию бота*

*Поддерживаемые операции:*
• `2 + 3 * 4` - Арифметические операции
• `x**2 + 3*x - 4` - Алгебраические уравнения  
• `diff(x**2, x)` - Производные
• `integrate(x**2, x)` - Интегралы
• `limit(sin(x)/x, x, 0)` - Пределы
• `solve(x**2 - 4, x)` - Решение уравнений

*Примеры запросов:*
• `реши 2*(3+5)/4`
• `производная x^2 + 3x`
• `интеграл x^2 dx` 
• `предел sin(x)/x при x->0`

🎨 *Особенности:*
• Поэтапное решение с объяснениями
• Красивое математическое оформление
• История ваших решений
• Интерактивные кнопки
        """
        
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            help_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    def preprocess_expression(self, text: str) -> str:
        """Предварительная обработка математического выражения"""
        # Замена русских команд на английские
        replacements = {
            'реши': '',
            'решить': '',
            'посчитай': '',
            'вычисли': '',
            'производная': 'diff',
            'интеграл': 'integrate', 
            'предел': 'limit',
            'упростить': 'simplify',
            'уравнение': 'solve'
        }
        
        for rus, eng in replacements.items():
            text = text.replace(rus, eng)
        
        # Замена ^ на ** для возведения в степень
        text = text.replace('^', '**')
        
        # Замена математических констант
        text = text.replace('π', 'pi')
        text = text.replace('∞', 'oo')
        
        # Удаление лишних пробелов
        text = ' '.join(text.split())
        
        return text.strip()
    
    def solve_expression(self, expression: str) -> dict:
        """Решение математического выражения с поэтапным объяснением"""
        try:
            steps = []
            result = None
            
            # Очистка выражения
            clean_expr = self.preprocess_expression(expression)
            steps.append(f"📝 *Исходное выражение:* `{expression}`")
            steps.append(f"🔧 *Обработанное выражение:* `{clean_expr}`")
            
            # Попытка численного вычисления
            try:
                if not any(c.isalpha() for c in clean_expr):
                    result = eval(clean_expr, {"__builtins__": {}}, 
                                {"sin": sp.sin, "cos": sp.cos, "tan": sp.tan,
                                 "log": sp.log, "exp": sp.exp, "sqrt": sp.sqrt,
                                 "pi": sp.pi, "E": sp.E, "oo": sp.oo})
                    steps.append(f"🔢 *Численное вычисление:* `{clean_expr} = {result}`")
                    return {
                        "success": True,
                        "result": result,
                        "steps": steps,
                        "type": "numeric"
                    }
            except:
                pass
            
            # Символьные вычисления
            x, y, z = symbols('x y z')
            
            # Определение типа выражения и решение
            if 'diff' in clean_expr:
                # Производная
                expr = clean_expr.replace('diff(', '').replace(')', '')
                parts = expr.split(',')
                if len(parts) == 2:
                    func = sp.sympify(parts[0].strip())
                    var = sp.sympify(parts[1].strip())
                    derivative = diff(func, var)
                    steps.append(f"📈 *Функция:* `{func}`")
                    steps.append(f"📊 *Переменная дифференцирования:* `{var}`")
                    steps.append(f"🎯 *Производная:* `{derivative}`")
                    result = derivative
                    
            elif 'integrate' in clean_expr:
                # Интеграл
                expr = clean_expr.replace('integrate(', '').replace(')', '')
                parts = expr.split(',')
                if len(parts) >= 2:
                    func = sp.sympify(parts[0].strip())
                    var = sp.sympify(parts[1].strip())
                    integral = integrate(func, var)
                    steps.append(f"📈 *Функция:* `{func}`")
                    steps.append(f"📊 *Переменная интегрирования:* `{var}`")
                    steps.append(f"🎯 *Интеграл:* `{integral}`")
                    result = integral
                    
            elif 'limit' in clean_expr:
                # Предел
                expr = clean_expr.replace('limit(', '').replace(')', '')
                parts = expr.split(',')
                if len(parts) >= 3:
                    func = sp.sympify(parts[0].strip())
                    var = sp.sympify(parts[1].strip())
                    point = sp.sympify(parts[2].strip())
                    lim = limit(func, var, point)
                    steps.append(f"📈 *Функция:* `{func}`")
                    steps.append(f"📊 *Переменная:* `{var}`")
                    steps.append(f"🎯 *Точка:* `{point}`")
                    steps.append(f"∞ *Предел:* `{lim}`")
                    result = lim
                    
            elif 'solve' in clean_expr or '=' in clean_expr:
                # Решение уравнений
                if 'solve' in clean_expr:
                    expr = clean_expr.replace('solve(', '').replace(')', '')
                    parts = expr.split(',')
                    equation = sp.sympify(parts[0].strip())
                    var = sp.sympify(parts[1].strip()) if len(parts) > 1 else x
                else:
                    equation = sp.sympify(clean_expr)
                    var = x
                
                solutions = solve(equation, var)
                steps.append(f"📝 *Уравнение:* `{equation} = 0`")
                steps.append(f"🎯 *Решения:* `{solutions}`")
                result = solutions
                
            else:
                # Общее символьное выражение
                expr = sp.sympify(clean_expr)
                simplified = simplify(expr)
                steps.append(f"📝 *Исходное выражение:* `{expr}`")
                steps.append(f"✨ *Упрощенное выражение:* `{simplified}`")
                result = simplified
            
            return {
                "success": True,
                "result": result,
                "steps": steps,
                "type": "symbolic"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "steps": [f"❌ *Ошибка при решении:* `{str(e)}`"]
            }
    
    def format_result(self, result_data: dict, expression: str, user_id: int) -> str:
        """Форматирование результата с красивым оформлением"""
        if user_id not in USER_HISTORY:
            USER_HISTORY[user_id] = []
        
        if result_data["success"]:
            response = f"🧮 *Результат решения:*\n\n"
            
            # Добавляем шаги решения
            for step in result_data["steps"]:
                response += f"{step}\n"
            
            response += f"\n🎯 *Финальный ответ:*\n"
            response += f"```\n{pretty(result_data['result'], use_unicode=True)}\n```"
            
            # Сохраняем в историю
            history_item = {
                "timestamp": datetime.now().isoformat(),
                "expression": expression,
                "result": str(result_data["result"]),
                "steps": result_data["steps"]
            }
            USER_HISTORY[user_id].append(history_item)
            if len(USER_HISTORY[user_id]) > 10:  # Ограничиваем историю
                USER_HISTORY[user_id] = USER_HISTORY[user_id][-10:]
                
        else:
            response = f"❌ *Ошибка!*\n\n"
            response += f"*Выражение:* `{expression}`\n"
            response += f"*Ошибка:* `{result_data['error']}`\n\n"
            response += "Попробуйте переформулировать запрос или используйте /help для справки."
        
        return response
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстовых сообщений"""
        user_message = update.message.text
        user_id = update.effective_user.id
        
        # Показываем что бот печатает
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        await asyncio.sleep(1)  # Имитация вычислений
        
        # Решаем выражение
        result_data = self.solve_expression(user_message)
        response_text = self.format_result(result_data, user_message, user_id)
        
        # Создаем клавиатуру с кнопками
        keyboard = [
            [InlineKeyboardButton("🔄 Решить другой пример", callback_data="solve_example")],
            [InlineKeyboardButton("📚 История", callback_data="history")],
            [InlineKeyboardButton("⬅️ Главное меню", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            response_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик нажатий на инлайн кнопки"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        if query.data == "solve_example":
            keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")]]
            await query.edit_message_text(
                "📝 *Отправьте математическое выражение для решения*\n\n"
                "Например:\n"
                "• `2 + 3 * 4`\n"
                "• `x**2 + 3*x - 4`\n" 
                "• `diff(x**2, x)`\n\n"
                "Я решу его поэтапно с подробными объяснениями! 🎯",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        elif query.data == "help":
            help_text = """
📖 *Справка по использованию бота*

*Поддерживаемые операции:*
• `2 + 3 * 4` - Арифметические операции
• `x**2 + 3*x - 4` - Алгебраические уравнения
• `diff(x**2, x)` - Производные  
• `integrate(x**2, x)` - Интегралы
• `limit(sin(x)/x, x, 0)` - Пределы

*Примеры запросов:*
• `реши 2*(3+5)/4`
• `производная x^2 + 3x`
• `интеграл x^2 dx`
• `предел sin(x)/x при x->0`
            """
            
            keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")]]
            await query.edit_message_text(
                help_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        elif query.data == "history":
            if user_id in USER_HISTORY and USER_HISTORY[user_id]:
                history_text = "📚 *История ваших решений:*\n\n"
                for i, item in enumerate(reversed(USER_HISTORY[user_id][-5:]), 1):
                    history_text += f"{i}. `{item['expression']}`\n"
                    history_text += f"   Результат: `{item['result'][:50]}{'...' if len(item['result']) > 50 else ''}`\n\n"
            else:
                history_text = "📚 *История решений пуста*\n\nРешите несколько примеров, и они появятся здесь!"
            
            keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")]]
            await query.edit_message_text(
                history_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        elif query.data == "back_to_main":
            keyboard = [
                [InlineKeyboardButton("🧮 Решить пример", callback_data="solve_example")],
                [InlineKeyboardButton("❓ Помощь", callback_data="help")],
                [InlineKeyboardButton("📚 История решений", callback_data="history")]
            ]
            await query.edit_message_text(
                "✨ *Главное меню* ✨\n\nВыберите действие:",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
    
    def run_bot(self):
        """Запуск бота"""
        logger.info("🤖 Бот запущен!")
        self.app.run_polling()

# Flask приложение для Render
@app.route('/')
def home():
    return "✅ Math Bot is running!"

@app.route('/health')
def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.route('/ping')
def ping():
    """Эндпоинт для пинга"""
    logger.info(f"🏓 Пинг получен - {datetime.now()}")
    return {"status": "pong", "timestamp": datetime.now().isoformat()}

def start_flask():
    """Запуск Flask приложения"""
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

def ping_self():
    """Функция для самопинга (запускается в отдельном потоке)"""
    import time
    while True:
        try:
            # Получаем URL приложения (на Render он доступен по своему домену)
            app_url = os.environ.get('RENDER_EXTERNAL_URL', 'http://localhost:5000')
            response = requests.get(f"{app_url}/ping", timeout=10)
            logger.info(f"🔔 Самопинг: {response.status_code} - {datetime.now()}")
        except Exception as e:
            logger.error(f"❌ Ошибка самопинга: {e}")
        time.sleep(300)  # Пинг каждые 5 минут

if __name__ == '__main__':
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN не установлен!")
        exit(1)
    
    # Создаем и запускаем бота
    bot = MathBot(BOT_TOKEN)
    
    # Запускаем Flask в отдельном потоке
    flask_thread = Thread(target=start_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # Запускаем самопинг в отдельном потоке
    ping_thread = Thread(target=ping_self)
    ping_thread.daemon = True
    ping_thread.start()
    
    # Запускаем бота (блокирующий вызов)
    bot.run_bot()
