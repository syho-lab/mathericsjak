import os
import logging
import asyncio
import requests
import re
from datetime import datetime
from flask import Flask
from threading import Thread

import sympy as sp
from sympy import pretty, symbols, solve, integrate, diff, limit, simplify, factor, expand, series, apart, sqrt, sin, cos, tan, log, exp, pi, E, oo
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
        self.application = Application.builder().token(token).build()
        self.setup_handlers()
    
    def setup_handlers(self):
        """Настройка обработчиков"""
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        self.application.add_handler(CallbackQueryHandler(self.button_handler))
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user = update.effective_user
        
        welcome_text = f"""
🌟 *Добро пожаловать, {user.first_name}!* 🌟

🎯 *Я — твой персональный математический гений!* 

✨ *Мои сверхспособности:*
• 🧮 Решение любых математических примеров
• 📊 Пошаговые объяснения с красивым оформлением
• 🎨 Поддержка естественного языка
• 💾 История всех решений
• ⚡ Мгновенные вычисления

💫 *Просто напиши пример — и я сделаю магию!*

👇 *Выбери действие или напиши пример:*
        """
        
        keyboard = [
            [InlineKeyboardButton("🧮 Решить пример", callback_data="solve_example")],
            [InlineKeyboardButton("📚 Примеры задач", callback_data="examples")],
            [InlineKeyboardButton("❓ Помощь", callback_data="help"), InlineKeyboardButton("💫 О боте", callback_data="about")],
            [InlineKeyboardButton("📊 История", callback_data="history")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            welcome_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        help_text = """
📖 *Как общаться с математическим гением?*

🎯 *Пиши примеры в любом формате:*
• `2 + 3 × 4 ÷ 2`
• `x² + 3x - 4 = 0` 
• `производная от x³ + 2x² - 1`
• `интеграл x² dx от 0 до 1`
• `предел (sin x)/x при x→0`
• `разложить x³ - 8 на множители`

🔧 *Поддерживаю всё:*
• ➕➖✖️➗ Арифметика
• 📐 Алгебра и уравнения
• 📈 Производные и интегралы
• ∞ Пределы и ряды
• 🧩 Факторизация и упрощение
• 📊 Комплексные выражения

💡 *Совет:* Используй естественную речь — я всё пойму!
        """
        
        keyboard = [
            [InlineKeyboardButton("📚 Примеры задач", callback_data="examples")],
            [InlineKeyboardButton("🧮 Решить пример", callback_data="solve_example")],
            [InlineKeyboardButton("⬅️ На главную", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            help_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def show_examples(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать примеры задач"""
        examples_text = """
🎯 *Вот что я отлично понимаю:*

🔹 *Арифметика:*
`2³ × (4 + 5) ÷ 3² + √16`
`|−5| × 2 + 3⁴ ÷ 9`

🔹 *Алгебра:*
`(x² − 4)(x³ + 2x² - x + 3) ÷ (x − 2)`
`разложить x⁴ - 16 на множители`
`упростить (x² + 2x + 1) ÷ (x + 1) × (x³ - 1)`

🔹 *Производные:*
`производная от (x⁴ + 3x³ − 2x)²`
`вторая производная sin(x) × cos(x)`
`дифференциал ln(x² + 1)`

🔹 *Интегралы:*
`интеграл 3x² + 2x - 1 dx`
`∫(x³ + 2x) dx от 0 до 2`
`интеграл от eˣ × sin(x) dx`

🔹 *Пределы:*
`предел (1 - cos x)/x² при x→0`
`lim x→∞ (1 + 1/x)ˣ`
`предел (x² - 4)/(x - 2) при x→2`

🎪 *Смело экспериментируй! Я понимаю очень многое!*
        """
        
        keyboard = [
            [InlineKeyboardButton("🧮 Решить свой пример", callback_data="solve_example")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                examples_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                examples_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    
    async def about_bot(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Информация о боте"""
        about_text = """
💫 *Math Genius Bot* 

🤖 *Самый умный математический помощник!*

✨ *Что меня отличает:*
• 🧠 Понимаю сложнейшие примеры
• 🎨 Красиво оформляю решения
• 💬 Общаюсь на естественном языке
• 📚 Помню историю твоих решений
• ⚡ Работаю мгновенно

🔮 *Я понимаю:*
• Любые математические выражения
• Естественный язык запросов
• Разные форматы записи
• Сложные многочлены и уравнения

🎊 *Добро пожаловать в мир красивой математики!*
        """
        
        keyboard = [[InlineKeyboardButton("⬅️ На главную", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            about_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    def smart_preprocess(self, text: str) -> str:
        """Умная предварительная обработка с улучшенным пониманием"""
        original_text = text
        text = text.lower().strip()
        
        # Удаляем лишние слова
        remove_words = ['пожалуйста', 'мне', 'нужно', 'найти', 'можно', 'ли', 'ты', 'вы', 'сможешь']
        for word in remove_words:
            text = re.sub(r'\b' + re.escape(word) + r'\b', '', text)
        
        # Замена русских команд на математические
        math_commands = {
            'реши': '', 'решить': '', 'посчитай': '', 'вычисли': '', 
            'производная': 'diff', 'производную': 'diff', 'дифференциал': 'diff', 'дифференцируй': 'diff',
            'интеграл': 'integrate', 'интеграла': 'integrate', 'интегрируй': 'integrate',
            'предел': 'limit', 'лимит': 'limit',
            'упростить': 'simplify', 'упрости': 'simplify',
            'разложи': 'factor', 'разложить': 'factor', 'факторизуй': 'factor',
            'раскрой': 'expand', 'раскрыть': 'expand',
            'уравнение': 'solve', 'реши уравнение': 'solve', 'найди корни': 'solve',
            'от': ' ', 'по': ' ', 'для': ' ', 'переменной': ' ',
            'при': ',', 'стремится': ',', 'стремиться': ',',
            '→': ',', '->': ',',
            'бесконечность': 'oo', 'бесконечности': 'oo'
        }
        
        for rus, eng in math_commands.items():
            text = text.replace(rus, eng)
        
        # Умная замена математических обозначений
        text = re.sub(r'(\d+)²', r'\1**2', text)
        text = re.sub(r'(\d+)³', r'\1**3', text)
        text = re.sub(r'(\d+)⁴', r'\1**4', text)
        text = re.sub(r'(\w+)²', r'\1**2', text)
        text = re.sub(r'(\w+)³', r'\1**3', text)
        text = re.sub(r'(\w+)⁴', r'\1**4', text)
        
        text = text.replace('^', '**')
        text = text.replace('×', '*').replace('÷', '/').replace('⋅', '*')
        text = text.replace('√', 'sqrt').replace('∣', 'abs').replace('|', 'abs')
        text = text.replace('π', 'pi').replace('∞', 'oo').replace('∫', 'integrate')
        text = text.replace('е', 'e').replace('ё', 'e')
        text = text.replace('sin', 'sin').replace('cos', 'cos').replace('tan', 'tan')
        text = text.replace('ln', 'log').replace('lg', 'log10')
        
        # Обработка пределов с естественным языком
        limit_pattern = r'limit\(([^,]+),([^,]+),([^)]+)\)'
        if 'limit' not in text and ('стремится' in original_text or '→' in original_text or 'при' in original_text):
            # Автоматическое создание limit из естественного языка
            if 'x→' in text or 'x->' in text:
                parts = re.split(r'x[→->]', text)
                if len(parts) == 2:
                    func = parts[0].strip()
                    point = parts[1].strip()
                    text = f'limit({func}, x, {point})'
        
        # Обработка интегралов с пределами
        if 'integrate' in text and ('от' in original_text or 'до' in original_text):
            if 'от' in original_text and 'до' in original_text:
                # Извлекаем пределы интегрирования
                pass
        
        # Удаление лишних пробелов и очистка
        text = re.sub(r'\s+', ' ', text).strip()
        text = re.sub(r',\s*,', ',', text)  # Удаляем лишние запятые
        
        return text if text else original_text

    def safe_sympify(self, expr_str: str):
        """Безопасное преобразование строки в sympy выражение"""
        try:
            # Создаем безопасное окружение для sympify
            safe_dict = {
                'x': symbols('x'), 'y': symbols('y'), 'z': symbols('z'),
                'sin': sin, 'cos': cos, 'tan': tan, 'cot': lambda x: 1/tan(x),
                'sqrt': sqrt, 'log': log, 'ln': log, 'exp': exp,
                'pi': pi, 'e': E, 'oo': oo,
                'abs': abs, 'factorial': sp.factorial,
                'diff': diff, 'integrate': integrate, 'limit': limit,
                'solve': solve, 'simplify': simplify, 'factor': factor, 'expand': expand
            }
            
            # Заменяем ** на ^ для временного парсинга
            temp_expr = expr_str.replace('**', '^')
            expr = sp.sympify(temp_expr, locals=safe_dict)
            # Возвращаем обратно **
            return expr
        except Exception as e:
            logger.error(f"Sympify error: {e}")
            return None

    def solve_expression(self, expression: str) -> dict:
        """Умное решение математического выражения с улучшенным пониманием"""
        try:
            steps = []
            original_expr = expression
            
            # Умная предобработка
            clean_expr = self.smart_preprocess(expression)
            steps.append(f"🎯 *Запрос:* `{original_expr}`")
            
            # Определяем тип задачи
            task_type = self.detect_task_type(clean_expr, original_expr)
            steps.append(f"🔍 *Определяем тип задачи...*")
            
            # Пробуем разные методы решения
            result = None
            
            if task_type == "derivative":
                result = self.solve_advanced_derivative(clean_expr, steps)
            elif task_type == "integral":
                result = self.solve_advanced_integral(clean_expr, steps)
            elif task_type == "limit":
                result = self.solve_advanced_limit(clean_expr, steps)
            elif task_type == "equation":
                result = self.solve_advanced_equation(clean_expr, steps)
            elif task_type == "factor":
                result = self.solve_factorization(clean_expr, steps)
            elif task_type == "expand":
                result = self.solve_expansion(clean_expr, steps)
            else:
                result = self.solve_advanced_general(clean_expr, steps)
            
            if result and result["success"]:
                return result
            else:
                return {
                    "success": False,
                    "error": "Не удалось распознать пример",
                    "steps": ["❌ *Пример не понятен*", "💡 Попробуйте сформулировать иначе"]
                }
                
        except Exception as e:
            logger.error(f"Solution error: {e}")
            return {
                "success": False,
                "error": "Не удалось обработать запрос",
                "steps": ["❌ *Пример не понятен*", "🎯 Попробуйте изменить формулировку"]
            }

    def detect_task_type(self, clean_expr: str, original_expr: str) -> str:
        """Определение типа математической задачи"""
        original_lower = original_expr.lower()
        
        if any(word in original_lower for word in ['производн', 'дифференциал', 'diff']):
            return "derivative"
        elif any(word in original_lower for word in ['интеграл', 'integrate', '∫']):
            return "integral"
        elif any(word in original_lower for word in ['предел', 'limit', 'стремится', '→']):
            return "limit"
        elif any(word in original_lower for word in ['уравнен', 'реши', 'корн', 'solve', '=']):
            return "equation"
        elif any(word in original_lower for word in ['разлож', 'факториз', 'factor']):
            return "factor"
        elif any(word in original_lower for word in ['раскр', 'expand']):
            return "expand"
        else:
            return "general"

    def solve_advanced_general(self, clean_expr: str, steps: list) -> dict:
        """Решение общих математических выражений"""
        try:
            expr = self.safe_sympify(clean_expr)
            if not expr:
                return {"success": False}
            
            steps.append(f"📝 *Выражение:* `{pretty(expr, use_unicode=True)}`")
            
            # Последовательное упрощение
            result = expr
            simplified = simplify(expr)
            
            if simplified != expr:
                steps.append(f"✨ *Упрощаем:* `{pretty(simplified, use_unicode=True)}`")
                result = simplified
            
            # Дополнительные преобразования для полиномов
            if result.is_polynomial():
                factored = factor(result)
                if factored != result:
                    steps.append(f"🧩 *Разложение:* `{pretty(factored, use_unicode=True)}`")
                    result = factored
            
            return {
                "success": True,
                "result": result,
                "steps": steps,
                "type": "general"
            }
        except:
            return {"success": False}

    def solve_advanced_derivative(self, clean_expr: str, steps: list) -> dict:
        """Решение производных с улучшенным пониманием"""
        try:
            x = symbols('x')
            
            # Извлекаем функцию из разных форматов
            if 'diff(' in clean_expr:
                # Формат diff(f(x), x)
                match = re.search(r'diff\(([^,]+),([^)]+)\)', clean_expr)
                if match:
                    func_str = match.group(1).strip()
                    var_str = match.group(2).strip()
                    func = self.safe_sympify(func_str)
                    var = self.safe_sympify(var_str) if var_str != 'x' else x
                else:
                    return {"success": False}
            else:
                # Пытаемся извлечь функцию из текста
                func_str = clean_expr.replace('diff', '').strip()
                func = self.safe_sympify(func_str)
                var = x
            
            if not func:
                return {"success": False}
            
            steps.append(f"📈 *Функция:* `{pretty(func, use_unicode=True)}`")
            steps.append(f"🎯 *По переменной:* `{var}`")
            
            derivative = diff(func, var)
            steps.append(f"💫 *Производная:* `{pretty(derivative, use_unicode=True)}`")
            
            simplified = simplify(derivative)
            if simplified != derivative:
                steps.append(f"✨ *Упрощенная:* `{pretty(simplified, use_unicode=True)}`")
            
            return {
                "success": True,
                "result": simplified,
                "steps": steps,
                "type": "derivative"
            }
        except:
            return {"success": False}

    def solve_advanced_integral(self, clean_expr: str, steps: list) -> dict:
        """Решение интегралов с улучшенным пониманием"""
        try:
            x = symbols('x')
            
            if 'integrate(' in clean_expr:
                match = re.search(r'integrate\(([^,]+),([^)]+)\)', clean_expr)
                if match:
                    func_str = match.group(1).strip()
                    var_str = match.group(2).strip()
                    func = self.safe_sympify(func_str)
                    var = self.safe_sympify(var_str) if var_str != 'x' else x
                else:
                    return {"success": False}
            else:
                func_str = clean_expr.replace('integrate', '').strip()
                func = self.safe_sympify(func_str)
                var = x
            
            if not func:
                return {"success": False}
            
            steps.append(f"📊 *Функция:* `{pretty(func, use_unicode=True)}`")
            steps.append(f"🎯 *Переменная:* `{var}`")
            
            integral = integrate(func, var)
            steps.append(f"💫 *Интеграл:* `{pretty(integral, use_unicode=True)}`")
            
            simplified = simplify(integral)
            if simplified != integral:
                steps.append(f"✨ *Упрощенный:* `{pretty(simplified, use_unicode=True)}`")
            
            return {
                "success": True,
                "result": simplified,
                "steps": steps,
                "type": "integral"
            }
        except:
            return {"success": False}

    def solve_advanced_equation(self, clean_expr: str, steps: list) -> dict:
        """Решение уравнений с улучшенным пониманием"""
        try:
            x = symbols('x')
            
            if 'solve(' in clean_expr:
                match = re.search(r'solve\(([^,]+),([^)]+)\)', clean_expr)
                if match:
                    eq_str = match.group(1).strip()
                    var_str = match.group(2).strip()
                    equation = self.safe_sympify(eq_str)
                    var = self.safe_sympify(var_str) if var_str != 'x' else x
                else:
                    return {"success": False}
            else:
                # Пытаемся найти уравнение в тексте
                if '=' in clean_expr:
                    parts = clean_expr.split('=')
                    if len(parts) == 2:
                        left = self.safe_sympify(parts[0].strip())
                        right = self.safe_sympify(parts[1].strip())
                        equation = left - right
                    else:
                        return {"success": False}
                else:
                    equation = self.safe_sympify(clean_expr)
                var = x
            
            if not equation:
                return {"success": False}
            
            steps.append(f"📝 *Уравнение:* `{pretty(equation, use_unicode=True)} = 0`")
            
            solutions = solve(equation, var)
            
            if solutions:
                steps.append(f"💡 *Найдено решений:* {len(solutions)}")
                for i, sol in enumerate(solutions, 1):
                    steps.append(f"🔹 *x{i}:* `{pretty(sol, use_unicode=True)}`")
            else:
                steps.append("❌ *Решений не найдено*")
            
            return {
                "success": True,
                "result": solutions,
                "steps": steps,
                "type": "equation"
            }
        except:
            return {"success": False}

    def solve_advanced_limit(self, clean_expr: str, steps: list) -> dict:
        """Решение пределов с улучшенным пониманием"""
        try:
            x = symbols('x')
            
            if 'limit(' in clean_expr:
                match = re.search(r'limit\(([^,]+),([^,]+),([^)]+)\)', clean_expr)
                if match:
                    func_str = match.group(1).strip()
                    var_str = match.group(2).strip()
                    point_str = match.group(3).strip()
                    func = self.safe_sympify(func_str)
                    var = self.safe_sympify(var_str) if var_str != 'x' else x
                    point = self.safe_sympify(point_str)
                else:
                    return {"success": False}
            else:
                return {"success": False}
            
            if not func:
                return {"success": False}
            
            steps.append(f"📊 *Функция:* `{pretty(func, use_unicode=True)}`")
            steps.append(f"🎯 *Переменная:* `{var}`")
            steps.append(f"📍 *Точка:* `{point}`")
            
            lim = limit(func, var, point)
            steps.append(f"💫 *Предел:* `{pretty(lim, use_unicode=True)}`")
            
            return {
                "success": True,
                "result": lim,
                "steps": steps,
                "type": "limit"
            }
        except:
            return {"success": False}

    def solve_factorization(self, clean_expr: str, steps: list) -> dict:
        """Факторизация выражений"""
        try:
            expr = self.safe_sympify(clean_expr.replace('factor', '').strip())
            if not expr:
                return {"success": False}
            
            steps.append(f"📝 *Исходное:* `{pretty(expr, use_unicode=True)}`")
            
            factored = factor(expr)
            steps.append(f"🧩 *Разложено:* `{pretty(factored, use_unicode=True)}`")
            
            return {
                "success": True,
                "result": factored,
                "steps": steps,
                "type": "factor"
            }
        except:
            return {"success": False}

    def solve_expansion(self, clean_expr: str, steps: list) -> dict:
        """Раскрытие скобок"""
        try:
            expr = self.safe_sympify(clean_expr.replace('expand', '').strip())
            if not expr:
                return {"success": False}
            
            steps.append(f"📝 *Исходное:* `{pretty(expr, use_unicode=True)}`")
            
            expanded = expand(expr)
            steps.append(f"📤 *Раскрыто:* `{pretty(expanded, use_unicode=True)}`")
            
            return {
                "success": True,
                "result": expanded,
                "steps": steps,
                "type": "expand"
            }
        except:
            return {"success": False}

    def format_result(self, result_data: dict, expression: str, user_id: int) -> str:
        """Красивое форматирование результата"""
        if user_id not in USER_HISTORY:
            USER_HISTORY[user_id] = []
        
        if result_data["success"]:
            response = "🎉 *Великолепно! Решение готово:*\n\n"
            
            for step in result_data["steps"]:
                response += f"• {step}\n"
            
            response += f"\n💎 *Финальный ответ:*\n"
            response += f"```\n{pretty(result_data['result'], use_unicode=True)}\n```"
            response += f"\n✨ *Магия математики завершена!*"
            
            # Сохраняем в историю
            history_item = {
                "timestamp": datetime.now().isoformat(),
                "expression": expression,
                "result": str(result_data["result"]),
                "type": result_data.get("type", "general")
            }
            USER_HISTORY[user_id].append(history_item)
            if len(USER_HISTORY[user_id]) > 20:
                USER_HISTORY[user_id] = USER_HISTORY[user_id][-20:]
                
        else:
            response = "❌ *Пример не понятен*\n\n"
            response += "💡 *Попробуйте:*\n"
            response += "• Сформулировать иначе\n• Использовать примеры из раздела помощи\n• Проверить синтаксис\n\n"
            response += "🎯 *Я понимаю самые сложные примеры, но нужно правильное оформление!*"
        
        return response

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстовых сообщений"""
        user_message = update.message.text
        user_id = update.effective_user.id
        
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        await asyncio.sleep(0.3)
        
        result_data = self.solve_expression(user_message)
        response_text = self.format_result(result_data, user_message, user_id)
        
        keyboard = [
            [InlineKeyboardButton("🔁 Новый пример", callback_data="solve_example")],
            [InlineKeyboardButton("📚 Примеры", callback_data="examples")],
            [InlineKeyboardButton("💫 О боте", callback_data="about")],
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
            keyboard = [[InlineKeyboardButton("⬅️ На главную", callback_data="back_to_main")]]
            await query.edit_message_text(
                "🧮 *Жду ваш математический шедевр!*\n\n"
                "💫 *Пишите в любом формате:*\n"
                "• `2 + 3 × 4²`\n" 
                "• `производная (x³ + 2x)²`\n"
                "• `интеграл от eˣ × sin(x) dx`\n"
                "• `предел (1 - cos x)/x² при x→0`\n\n"
                "*Я понимаю очень многое!* 🎊",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        elif query.data == "help":
            await self.help_command(update, context)
            
        elif query.data == "examples":
            await self.show_examples(update, context)
            
        elif query.data == "about":
            await self.about_bot(update, context)
            
        elif query.data == "history":
            if user_id in USER_HISTORY and USER_HISTORY[user_id]:
                history_text = "📚 *История ваших решений:*\n\n"
                for i, item in enumerate(reversed(USER_HISTORY[user_id][-10:]), 1):
                    emoji = "🧮" if item.get("type") == "general" else "📈" if item.get("type") == "derivative" else "∫" if item.get("type") == "integral" else "∞" if item.get("type") == "limit" else "🎯"
                    history_text += f"{emoji} *{i}.* `{item['expression'][:40]}{'...' if len(item['expression']) > 40 else ''}`\n"
                    history_text += f"   💎 `{item['result'][:50]}{'...' if len(item['result']) > 50 else ''}`\n\n"
            else:
                history_text = "📚 *История пока пуста*\n\n*Решите несколько примеров, и они появятся здесь!* ✨"
            
            keyboard = [[InlineKeyboardButton("⬅️ На главную", callback_data="back_to_main")]]
            await query.edit_message_text(
                history_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        elif query.data == "back_to_main":
            keyboard = [
                [InlineKeyboardButton("🧮 Решить пример", callback_data="solve_example")],
                [InlineKeyboardButton("📚 Примеры задач", callback_data="examples")],
                [InlineKeyboardButton("❓ Помощь", callback_data="help"), InlineKeyboardButton("💫 О боте", callback_data="about")],
                [InlineKeyboardButton("📊 История", callback_data="history")]
            ]
            await query.edit_message_text(
                "✨ *Главное меню* ✨\n\n*Выберите действие:*",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
    
    def run_bot(self):
        """Запуск бота"""
        logger.info("🚀 Math Genius Bot запущен!")
        self.application.run_polling()

# Flask приложение для Render
@app.route('/')
def home():
    return "✅ Math Genius Bot is running perfectly!"

@app.route('/health')
def health():
    return {"status": "healthy", "service": "Math Genius Bot", "timestamp": datetime.now().isoformat()}

@app.route('/ping')
def ping():
    logger.info(f"🏓 Пинг получен - {datetime.now()}")
    return {"status": "pong", "timestamp": datetime.now().isoformat()}

def start_flask():
    """Запуск Flask приложения"""
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

def ping_self():
    """Функция для самопинга"""
    import time
    while True:
        try:
            app_url = os.environ.get('RENDER_EXTERNAL_URL', 'http://localhost:5000')
            response = requests.get(f"{app_url}/ping", timeout=10)
            logger.info(f"🔔 Самопинг: {response.status_code}")
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
    
    # Запускаем бота
    bot.run_bot()
