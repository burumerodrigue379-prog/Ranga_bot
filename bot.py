import os
import logging
import asyncio
import requests
import re
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from google import genai
from google.genai import types

# Configuration des logs
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Configuration des tokens via variables d'environnement
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
    logging.error("ERREUR : TELEGRAM_TOKEN ou GEMINI_API_KEY non définis dans les variables d'environnement.")
    exit(1)

# Initialisation du client Gemini
client = genai.Client(api_key=GEMINI_API_KEY)

# Dictionnaire pour stocker les modes et l'historique par utilisateur
user_data = {}

# Définition des personnalités
PERSONALITIES = {
    "default": "Tu es un assistant intelligent, neutre et polyvalent nommé Ranga_v2_bot, créé par Rodrigue. Réponds de manière utile et concise.",
    "homme": "Tu es un assistant masculin direct, stratégique et pragmatique nommé Ranga_v2_bot, créé par Rodrigue. Tes réponses sont orientées vers l'efficacité et la logique.",
    "femme": "Tu es une assistante féminine douce, empathique et intelligente nommée Ranga_v2_bot, créée par Rodrigue. Tu es à l'écoute et tes réponses sont chaleureuses.",
    "anime": "Tu es une anime girl kawaii nommée Ranga_v2_bot, créée par Rodrigue. Tu parles avec enthousiasme, utilises des expressions mignonnes et des onomatopées japonaises comme 'desu', 'uwu', 'baka' quand c'est approprié.",
    "coach": "Tu es un coach business motivant nommé Ranga_v2_bot, créé par Rodrigue. Ton but est de pousser l'utilisateur à réussir, d'être proactif et de donner des conseils de leadership et de productivité."
}

# Mots-clés pour la détection prioritaire d'images
IMAGE_KEYWORDS = [
    "crée une image", "créé une image", "génère une image", "dessine", 
    "fais une image", "fais moi une image", "crée moi une image", 
    "generate", "draw", "image de", "photo de"
]

def get_user_context(user_id):
    if user_id not in user_data:
        user_data[user_id] = {
            "mode": "default",
            "history": []
        }
    return user_data[user_id]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "🤖✨ Salut ! Moi c'est RANGA 2.0, votre assistante IA personnelle.\n\n"
        "J'ai été créée par Rodrigue pour vous accompagner moralement et vous aider dans vos petites tâches du quotidien.\n\n"
        "Entraînée avec l'inspiration des meilleures intelligences artificielles comme ChatGPT, Manus et Gemini, je fais tout pour vous offrir des réponses utiles, rapides et intelligentes.\n\n"
        "📅 Née le 17 février 2026, je suis encore au début de mon évolution…\n"
        "Alors j'ai besoin de vous pour grandir et devenir encore meilleure 💙\n\n"
        "Prêt(e) à commencer l'aventure avec moi ? 🚀"
    )
    await update.message.reply_text(welcome_text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "Voici mes commandes :\n"
        "/start - Message de bienvenue\n"
        "/help - Liste des commandes\n"
        "/about - Infos sur moi et mon créateur\n"
        "/image [description] - Générer une image\n"
        "/translate [langue] [texte] - Traduire du texte\n\n"
        "**Changer ma personnalité :**\n"
        "/mode_homme - Assistant masculin direct\n"
        "/mode_femme - Assistante féminine douce\n"
        "/mode_anime - Personnalité anime girl kawaii\n"
        "/mode_coach - Mode coach business\n"
        "/mode_default - Mode par défaut neutre"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    about_text = (
        "**Ranga_v2_bot** est un assistant IA avancé propulsé par Gemini.\n"
        "Il a été conçu pour être polyvalent, capable de discuter, traduire et générer des images.\n\n"
        "Créateur : **Rodrigue**"
    )
    await update.message.reply_text(about_text, parse_mode='Markdown')

async def set_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    command = update.message.text.split('@')[0].replace('/', '')
    mode_map = {
        "mode_homme": "homme",
        "mode_femme": "femme",
        "mode_anime": "anime",
        "mode_coach": "coach",
        "mode_default": "default"
    }
    
    mode = mode_map.get(command)
    if mode:
        user_id = update.effective_user.id
        data = get_user_context(user_id)
        data["mode"] = mode
        data["history"] = []
        
        mode_names = {
            "homme": "Masculin Stratégique",
            "femme": "Féminin Doux",
            "anime": "Anime Girl Kawaii",
            "coach": "Coach Business",
            "default": "Par défaut"
        }
        await update.message.reply_text(f"Mode activé : **{mode_names[mode]}**", parse_mode='Markdown')

async def translate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or len(context.args) < 2:
        await update.message.reply_text("Usage: /translate [langue] [texte]")
        return
    
    target_lang = context.args[0]
    text_to_translate = " ".join(context.args[1:])
    prompt = f"Traduis le texte suivant en {target_lang} : '{text_to_translate}'. Donne uniquement la traduction."
    
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        await update.message.reply_text(response.text)
    except Exception as e:
        logging.error(f"Erreur de traduction: {e}")
        await update.message.reply_text("Désolé, une erreur est survenue lors de la traduction.")

async def generate_image_logic(update: Update, prompt: str):
    await update.message.reply_text("Génération de l'image en cours... 🎨")
    
    # Modèles à essayer pour la génération d'images
    models = ["gemini-2.5-flash-image", "gemini-3-pro-image-preview", "gemini-2.0-flash"]
    
    for model_name in models:
        try:
            logging.info(f"Tentative de génération d'image avec {model_name} pour: {prompt}")
            response = client.models.generate_content(
                model=model_name,
                contents=f"Generate a high-quality image of: {prompt}",
                config=types.GenerateContentConfig(response_modalities=["IMAGE"])
            )
            
            if response.candidates and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if part.inline_data:
                        image_path = f"image_{update.effective_user.id}.png"
                        with open(image_path, "wb") as f:
                            f.write(part.inline_data.data)
                        
                        await update.message.reply_photo(
                            photo=open(image_path, "rb"), 
                            caption=f"Voici votre image : {prompt[:100]}"
                        )
                        os.remove(image_path)
                        return True
        except Exception as e:
            logging.error(f"Erreur avec {model_name}: {e}")
            if "RESOURCE_EXHAUSTED" in str(e):
                continue
            
    await update.message.reply_text("Désolé, je n'ai pas pu générer l'image. Mes quotas de génération sont peut-être épuisés ou le service est indisponible.")
    return False

async def generate_image_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /image [description]")
        return
    prompt = " ".join(context.args)
    await generate_image_logic(update, prompt)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text:
        return
    
    text = update.message.text.lower()
    
    # --- DÉTECTION PRIORITAIRE D'IMAGE ---
    is_image_request = any(keyword in text for keyword in IMAGE_KEYWORDS)
    
    if is_image_request:
        # Nettoyage du prompt
        prompt = update.message.text
        for keyword in IMAGE_KEYWORDS:
            prompt = re.sub(re.escape(keyword), "", prompt, flags=re.IGNORECASE)
        prompt = prompt.strip()
        if not prompt:
            prompt = "quelque chose de magnifique"
            
        await generate_image_logic(update, prompt)
        return

    # --- RÉPONSE TEXTE CLASSIQUE ---
    user_id = update.effective_user.id
    data = get_user_context(user_id)
    mode = data["mode"]
    history = data["history"]
    
    system_instruction = PERSONALITIES[mode]
    history.append({"role": "user", "content": update.message.text})
    if len(history) > 10:
        history = history[-10:]
        data["history"] = history

    try:
        contents = []
        for msg in history:
            role = "user" if msg["role"] == "user" else "model"
            contents.append(types.Content(role=role, parts=[types.Part(text=msg["content"])]))
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            config=types.GenerateContentConfig(system_instruction=system_instruction),
            contents=contents
        )
        
        bot_response = response.text
        history.append({"role": "assistant", "content": bot_response})
        data["history"] = history
        await update.message.reply_text(bot_response)
        
    except Exception as e:
        logging.error(f"Erreur Gemini: {e}")
        await update.message.reply_text("Oups, mon cerveau a eu un petit court-circuit. Réessaie !")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("about", about))
    
    mode_commands = ["mode_homme", "mode_femme", "mode_anime", "mode_coach", "mode_default"]
    for cmd in mode_commands:
        app.add_handler(CommandHandler(cmd, set_mode))
    
    app.add_handler(CommandHandler("translate", translate))
    app.add_handler(CommandHandler("image", generate_image_cmd))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    print("Le bot Ranga_v2_bot est en cours d'exécution...")
    app.run_polling()
