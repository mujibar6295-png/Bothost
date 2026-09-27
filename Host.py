import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
import subprocess
import os
import re

# Apnar dewa token ekhane add kora hoyeche
TOKEN = '8710736330:AAHsNib6LNJsaNAYBiIHAv6zgCKvXwyCTbs'
bot = telebot.TeleBot(TOKEN)

running_bots = {}
deploy_sessions = {} # User der deploy step gulo track korar jonno (kon file pathalo)

# Main Keyboard
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
    # Reply keyboard remove kore dicchi jate chat clean thake
    msg = bot.send_message(message.chat.id, "Apnar bot er `.py` file ta ekhane send korun...", reply_markup=ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, handle_py_file)

def handle_py_file(message):
    if not message.document or not message.document.file_name.endswith('.py'):
        msg = bot.send_message(message.chat.id, "❌ Doya kore ekta valid .py file send korun! (Try again 🚀 Deploy Bot)", reply_markup=get_main_keyboard())
        return

    bot.send_message(message.chat.id, "⏳ Python File downloading...")
    
    # .py File Download
    file_info = bot.get_file(message.document.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    file_name = message.document.file_name
    
    with open(file_name, 'wb') as new_file:
        new_file.write(downloaded_file)
        
    # State save korchi
    deploy_sessions[message.chat.id] = {'py_file': file_name}
    
    # Requirements.txt er jonno Skip button
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(KeyboardButton("⏭️ Skip"))
    
    msg = bot.send_message(
        message.chat.id, 
        f"✅ `{file_name}` downloaded!\n\nEbar jodi apnar kono `requirements.txt` file thake, seta send korun.\nNa thakle nicher **Skip** button a click korun.", 
        reply_markup=markup,
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, handle_requirements_file)


def handle_requirements_file(message):
    user_session = deploy_sessions.get(message.chat.id)
    if not user_session:
        return
        
    py_file_name = user_session['py_file']

    if message.text == "⏭️ Skip":
        bot.send_message(message.chat.id, "⏩ Skipped requirements.txt. Auto-detecting packages...", reply_markup=get_main_keyboard())
        run_bot_process(message.chat.id, py_file_name, req_file=None)
        
    elif message.document and message.document.file_name == 'requirements.txt':
        bot.send_message(message.chat.id, "⏳ Downloading requirements.txt...", reply_markup=get_main_keyboard())
        
        # Req File Download
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        req_file_name = f"req_{message.chat.id}.txt" # Unique name to avoid clash
        
        with open(req_file_name, 'wb') as new_file:
            new_file.write(downloaded_file)
            
        bot.send_message(message.chat.id, "📦 Installing packages from requirements.txt...")
        
        try:
            # Pip install requirements
            subprocess.run(['pip', 'install', '-r', req_file_name], check=True)
            bot.send_message(message.chat.id, "✅ All packages installed successfully!")
            os.remove(req_file_name) # Remove req file after install
            
        except subprocess.CalledProcessError as e:
            bot.send_message(message.chat.id, f"⚠️ Requirements install a problem hoyeche. Error: {e}")
            
        run_bot_process(message.chat.id, py_file_name, req_file=True)
        
    else:
        # Jodi onno kichu ba vul jinish pathay
        msg = bot.send_message(message.chat.id, "❌ Please ekta valid `requirements.txt` send korun ba 'Skip' e click korun.")
        bot.register_next_step_handler(msg, handle_requirements_file)


def run_bot_process(chat_id, py_file_name, req_file=None):
    # Jodi req file na thake, tahole auto install (Aager code er logic)
    if not req_file:
        try:
            with open(py_file_name, 'r') as f:
                code_content = f.read()
                imports = re.findall(r'^(?:import|from)\s+([a-zA-Z0-9_]+)', code_content, re.MULTILINE)
                unique_imports = set(imports)
                
                for module in unique_imports:
                    bot.send_message(chat_id, f"📦 Auto-Installing {module}...")
                    subprocess.run(['pip', 'install', module], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            bot.send_message(chat_id, f"⚠️ Dependency check error: {e}")

    # Run the bot in background
    try:
        process = subprocess.Popen(["python", py_file_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        if chat_id not in running_bots:
            running_bots[chat_id] = {}
            
        running_bots[chat_id][py_file_name] = process
        
        bot.send_message(
            chat_id, 
            f"🎉 **Bot Successfully Deployed!**\n\n📁 File: `{py_file_name}` is now live in the background.", 
            parse_mode="Markdown"
        )
        
    except Exception as e:
        bot.send_message(chat_id, f"❌ Bot start korte problem hoyeche: {e}")
        
    # Clear session
    if chat_id in deploy_sessions:
        del deploy_sessions[chat_id]

# ==================== MANAGE BOT LOGIC ====================
@bot.message_handler(func=lambda message: message.text == "⚙️ Manage Bot")
def manage_bots(message):
    user_bots = running_bots.get(message.chat.id, {})
    
    if not user_bots:
        bot.send_message(message.chat.id, "🤷‍♂️ Apnar kono bot live nei ekhon.")
        return
        
    markup = InlineKeyboardMarkup()
    for b_name in user_bots.keys():
        markup.add(
            InlineKeyboardButton(f"🛑 Stop {b_name}", callback_data=f"stop_{b_name}"),
            InlineKeyboardButton(f"🗑 Delete {b_name}", callback_data=f"del_{b_name}")
        )
        
    bot.send_message(message.chat.id, "👇 Niche theke apnar bot manage korun:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('stop_') or call.data.startswith('del_'))
def handle_management(call):
    action, bot_name = call.data.split('_', 1)
    user_id = call.message.chat.id
    
    process = running_bots.get(user_id, {}).get(bot_name)
    
    if process:
        process.terminate() # Kill the background process
        
        if action == 'del':
            del running_bots[user_id][bot_name]
            if os.path.exists(bot_name):
                os.remove(bot_name) # Server theke py file delete korbe
            bot.answer_callback_query(call.id, f"{bot_name} Deleted!")
            bot.edit_message_text(f"🗑 `{bot_name}` file deleted ar bot stopped.", user_id, call.message.message_id, parse_mode="Markdown")
        else:
            bot.answer_callback_query(call.id, f"{bot_name} Stopped!")
            bot.edit_message_text(f"🛑 `{bot_name}` ekhon paused/stopped ache.", user_id, call.message.message_id, parse_mode="Markdown")
    else:
        bot.answer_callback_query(call.id, "Bot already stopped ba not found!", show_alert=True)

print("Main Host Bot is running...")
bot.infinity_polling()
