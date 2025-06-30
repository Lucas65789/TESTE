import os
import json
import uuid
import shutil
import subprocess
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

BOT_REGISTRY_FILE = 'bot_registry.json'
BOTS_FOLDER = 'bots_ativos'
MODELO_BOT = 'modelo_bot.py'

processos = {}

os.makedirs(BOTS_FOLDER, exist_ok=True)

def load_registry():
    if not os.path.exists(BOT_REGISTRY_FILE):
        return {}
    with open(BOT_REGISTRY_FILE, 'r') as f:
        return json.load(f)

def save_registry(data):
    with open(BOT_REGISTRY_FILE, 'w') as f:
        json.dump(data, f, indent=2)

registry = load_registry()

def iniciar_bot(uid, token):
    script_path = os.path.join(BOTS_FOLDER, f'{uid}.py')
    shutil.copyfile(MODELO_BOT, script_path)
    proc = subprocess.Popen(['python3', script_path, token])
    processos[uid] = proc

def parar_bot(uid):
    proc = processos.get(uid)
    if proc:
        proc.terminate()
        proc.wait()
        processos.pop(uid, None)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Envie o token do seu bot para iniciá-lo.")

async def handle_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    token = update.message.text.strip()
    uid = str(uuid.uuid4())[:8]
    try:
        iniciar_bot(uid, token)
        registry[uid] = {"token": token, "user_id": update.effective_user.id}
        save_registry(registry)
        await update.message.reply_text(f"✅ Bot iniciado!
ID: {uid}", reply_markup=gerar_botoes(uid))
    except Exception as e:
        await update.message.reply_text(f"Erro ao iniciar bot: {e}")

def gerar_botoes(uid):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🔴 Parar", callback_data=f"parar:{uid}"),
        InlineKeyboardButton("♻️ Reiniciar", callback_data=f"reiniciar:{uid}")
    ]])

async def botao_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action, uid = query.data.split(":")

    if uid not in registry:
        await query.edit_message_text("❌ Bot não encontrado.")
        return

    if action == "parar":
        parar_bot(uid)
        await query.edit_message_text("🔴 Bot parado.")
    elif action == "reiniciar":
        parar_bot(uid)
        iniciar_bot(uid, registry[uid]["token"])
        await query.edit_message_text("♻️ Bot reiniciado.", reply_markup=gerar_botoes(uid))

async def listar_bots_usuario(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    bots_do_usuario = {uid: data for uid, data in registry.items() if data["user_id"] == user_id}

    if not bots_do_usuario:
        await update.message.reply_text("❌ Você ainda não cadastrou nenhum bot.")
        return

    for uid in bots_do_usuario:
        texto = f"🤖 Bot ID: `{uid}`\nStatus: {'🟢 Ativo' if uid in processos else '🔴 Parado'}"
        await update.message.reply_text(texto, parse_mode='Markdown', reply_markup=gerar_botoes(uid))

def restaurar_bots():
    for uid, data in registry.items():
        try:
            iniciar_bot(uid, data["token"])
            print(f"✅ Bot {uid} restaurado.")
        except Exception as e:
            print(f"Erro ao restaurar {uid}: {e}")

async def main():
    app = ApplicationBuilder().token("7306325518:AAFcWXX-usCkHpzQcefs80JqAxO32cVL05E").build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("meusbots", listar_bots_usuario))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_token))
    app.add_handler(CallbackQueryHandler(botao_callback))

    restaurar_bots()
    print("🤖 Bot hospedeiro iniciado.")
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

