import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
import subprocess
import os
import re
import json
import sys
import time

# Bot Token
TOKEN = '8710736330:AAHsNib6LNJsaNAYBiIHAv6zgCKvXwyCTbs'
bot = telebot.TeleBot(TOKEN)

# ==================== DATA STORAGE (PERSISTENCE) ====================
DATA_FILE = "bot_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# Load existing database
running_bots_db = load_data()
deploy_sessions = {}
active_processes = {}  # Active running process handles

def restart_saved_bots():
    """Bot restart hole aager running bot gulo automatically restore korbe"""
    print("Checking and restoring previous bots...")
    for chat_id_str, user_bots in list(running_bots_db.items()):
        chat_id = int(chat_id_str)
        for original_name, info in list(user_bots.items()):
            if info.get('status') == 'running':
                actual_file = info.get('file_path')
                if actual_file and os.path.exists(actual_file):
                    print(f"Restarting: {original_name} (User: {chat_id})")
                    start_bot_process(chat_id, original_name, actual_file)

# ==================== MAIN KEYBOARD ====================
def get_main_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(KeyboardButton("🚀 Deploy Bot"), KeyboardButton("⚙️ Manage Bot"))
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id, 
        "Welcome to Bot Hoster! 🤖\n\nNiche theke option select korun:", 
        reply_markup=get_main_keyboard()
    )

# ==================== DEPLOY BOT LOGIC ====================
@bot.message_handler(func=lambda message: message.text == "🚀 Deploy Bot")
def deploy_bot_prompt(message):
    msg = bot.send_message(
        message.chat.id, 
        "Apnar bot er `.py` file ta ekhane send korun...", 
        reply_markup=ReplyKeyboardRemove()
    )
    bot.register_next_step_handler(msg, handle_py_file)

def handle_py_file(message):
    if not message.document or not message.document.file_name.endswith('.py'):
        bot.send_message(
            message.chat.id, 
            "❌ Doya kore ekta valid .py file send korun! (Try again 🚀 Deploy Bot)", 
            reply_markup=get_main_keyboard()
        )
        return

    bot.send_message(message.chat.id, "⏳ Python File downloading...")
    
    file_info = bot.get_file(message.document.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    
    original_name = message.document.file_name
    unique_file_name = f"{message.chat.id}_{int(time.time())}_{original_name}"
    
    with open(unique_file_name, 'wb') as new_file:
        new_file.write(downloaded_file)
        
    deploy_sessions[message.chat.id] = {
        'original_name': original_name,
        'unique_file': unique_file_name
    }
    
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(KeyboardButton("⏭️ Skip"))
    
    msg = bot.send_message(
        message.chat.id, 
        f"✅ `{original_name}` downloaded!\n\nEbar jodi apnar kono `requirements.txt` file thake, seta send korun.\nNa thakle nicher **Skip** button a click korun.", 
        reply_markup=markup,
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, handle_requirements_file)

def handle_requirements_file(message):
    user_session = deploy_sessions.get(message.chat.id)
    if not user_session:
        return
        
    original_name = user_session['original_name']
    unique_file = user_session['unique_file']

    if message.text == "⏭️ Skip":
        bot.send_message(message.chat.id, "⏩ Skipped requirements.txt. Auto-detecting modules...", reply_markup=get_main_keyboard())
        install_dependencies_and_run(message.chat.id, original_name, unique_file, req_file=None)
        
    elif message.document and message.document.file_name == 'requirements.txt':
        bot.send_message(message.chat.id, "⏳ Downloading requirements.txt...", reply_markup=get_main_keyboard())
        
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        req_file_name = f"req_{message.chat.id}_{int(time.time())}.txt"
        
        with open(req_file_name, 'wb') as new_file:
            new_file.write(downloaded_file)
            
        bot.send_message(message.chat.id, "📦 Installing packages from requirements.txt...")
        
        try:
            subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', req_file_name], check=True)
            bot.send_message(message.chat.id, "✅ All packages installed successfully!")
            os.remove(req_file_name)
        except subprocess.CalledProcessError as e:
            bot.send_message(message.chat.id, f"⚠️ Requirements install a problem hoyeche. Error: {e}")
            
        install_dependencies_and_run(message.chat.id, original_name, unique_file, req_file=True)
    else:
        msg = bot.send_message(message.chat.id, "❌ Please ekta valid `requirements.txt` send korun ba 'Skip' e click korun.")
        bot.register_next_step_handler(msg, handle_requirements_file)

def install_dependencies_and_run(chat_id, original_name, unique_file, req_file=None):
    if not req_file:
        try:
            with open(unique_file, 'r', encoding='utf-8', errors='ignore') as f:
                code_content = f.read()
                imports = re.findall(r'^(?:import|from)\s+([a-zA-Z0-9_]+)', code_content, re.MULTILINE)
                unique_imports = set(imports)
                
                skip_modules = {'os', 'sys', 'time', 're', 'json', 'math', 'datetime', 'threading', 'asyncio', 'subprocess', 'random'}
                for module in unique_imports:
                    if module not in skip_modules:
                        subprocess.run([sys.executable, '-m', 'pip', 'install', module], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            bot.send_message(chat_id, f"⚠️ Dependency detection error: {e}")

    bot.send_message(chat_id, "⏳ Bot start kora hocche...")
    
    success, msg = start_bot_process(chat_id, original_name, unique_file)
    
    if success:
        bot.send_message(
            chat_id, 
            f"🎉 **Bot Successfully Deployed & Running!**\n\n📁 File: `{original_name}`\n🟢 Status: Active in background.", 
            parse_mode="Markdown"
        )
    else:
        bot.send_message(
            chat_id, 
            f"❌ **Bot start hote pareni / Crash koreche!**\n\n**Error Log:**\n```\n{msg}\n```", 
            parse_mode="Markdown"
        )
        
    if chat_id in deploy_sessions:
        del deploy_sessions[chat_id]

def start_bot_process(chat_id, original_name, unique_file):
    chat_id_str = str(chat_id)
    log_file_name = f"{unique_file}.log"
    
    try:
        # Aage jodi oi bot ta running thake, ager ta stop kora hobe
        if chat_id in active_processes and original_name in active_processes[chat_id]:
            old_proc = active_processes[chat_id][original_name]
            if old_proc.poll() is None:
                old_proc.terminate()
        
        # Log file open kore subprocess pass kora hoyeche (Deadlock hobe na)
        log_file = open(log_file_name, "w", encoding="utf-8")
        process = subprocess.Popen(
            [sys.executable, unique_file], 
            stdout=log_file, 
            stderr=subprocess.STDOUT
        )
        
        # 2 second pause kore check korchi script ta crash korlo kina
        time.sleep(2)
        if process.poll() is not None:
            log_file.close()
            with open(log_file_name, "r", encoding="utf-8", errors="ignore") as lf:
                error_output = lf.read().strip()[-700:]
            return False, error_output if error_output else "Process exited immediately with error code 1."

        # Database e status save
        if chat_id_str not in running_bots_db:
            running_bots_db[chat_id_str] = {}
            
        running_bots_db[chat_id_str][original_name] = {
            "file_path": unique_file,
            "log_path": log_file_name,
            "status": "running"
        }
        save_data(running_bots_db)
        
        # Memory tracking
        if chat_id not in active_processes:
            active_processes[chat_id] = {}
        active_processes[chat_id][original_name] = process
        
        return True, "Running"
        
    except Exception as e:
        return False, str(e)

# ==================== MANAGE BOT LOGIC ====================
@bot.message_handler(func=lambda message: message.text == "⚙️️ Manage Bot")
def manage_bots(message):
    chat_id_str = str(message.chat.id)
    user_bots = running_bots_db.get(chat_id_str, {})
    
    if not user_bots:
        bot.send_message(message.chat.id, "🤷‍♂️ Apnar kono bot deploy kora nei.")
        return
        
    markup = InlineKeyboardMarkup()
    for b_name, info in user_bots.items():
        status_icon = "🟢" if info.get('status') == 'running' else "🛑"
        markup.add(
            InlineKeyboardButton(f"{status_icon} Stop {b_name}", callback_data=f"stop_{b_name}"),
            InlineKeyboardButton(f"🗑 Delete {b_name}", callback_data=f"del_{b_name}")
        )
        markup.add(
            InlineKeyboardButton(f"📄 View Logs ({b_name})", callback_data=f"log_{b_name}")
        )
        
    bot.send_message(message.chat.id, "👇 Niche theke apnar bot manage korun:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: any(call.data.startswith(x) for x in ['stop_', 'del_', 'log_']))
def handle_management(call):
    action, bot_name = call.data.split('_', 1)
    chat_id = call.message.chat.id
    chat_id_str = str(chat_id)
    
    user_bots = running_bots_db.get(chat_id_str, {})
    bot_info = user_bots.get(bot_name)
    
    if not bot_info:
        bot.answer_callback_query(call.id, "Bot not found!", show_alert=True)
        return

    process = active_processes.get(chat_id, {}).get(bot_name)

    if action == 'log':
        log_path = bot_info.get('log_path')
        if log_path and os.path.exists(log_path):
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                logs = f.read().strip()[-1000:]
            msg = logs if logs else "No logs yet. Bot is running normally."
            bot.send_message(chat_id, f"📄 **Logs for `{bot_name}`:**\n```\n{msg}\n```", parse_mode="Markdown")
        else:
            bot.send_message(chat_id, "Log file not found.")
        bot.answer_callback_query(call.id)
        return

    if action == 'stop':
        if process and process.poll() is None:
            process.terminate()
        bot_info['status'] = 'stopped'
        save_data(running_bots_db)
        bot.answer_callback_query(call.id, f"{bot_name} Stopped!")
        bot.edit_message_text(f"🛑 `{bot_name}` successfully stopped.", chat_id, call.message.message_id, parse_mode="Markdown")

    elif action == 'del':
        if process and process.poll() is None:
            process.terminate()
            
        file_path = bot_info.get('file_path')
        log_path = bot_info.get('log_path')
        
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        if log_path and os.path.exists(log_path):
            os.remove(log_path)
            
        del running_bots_db[chat_id_str][bot_name]
        save_data(running_bots_db)
        
        if chat_id in active_processes and bot_name in active_processes[chat_id]:
            del active_processes[chat_id][bot_name]
            
        bot.answer_callback_query(call.id, f"{bot_name} Deleted!")
        bot.edit_message_text(f"🗑 `{bot_name}` file delete kora hoyeche.", chat_id, call.message.message_id, parse_mode="Markdown")

# Main host bot run howar somoy aager bot auto restart hobe
restart_saved_bots()

print("Main Host Bot is running...")
bot.infinity_polling()
