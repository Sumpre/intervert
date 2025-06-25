from flask import Flask, request, render_template, session, redirect, url_for
import discord
from discord import app_commands
from discord.ext import commands
import requests
import os
import threading

# --- CONFIGURAZIONE ---
# Leggiamo tutte le 6 variabili d'ambiente che hai impostato su Render.
try:
    CLIENT_ID = os.environ['CLIENT_ID']
    CLIENT_SECRET = os.environ['CLIENT_SECRET']
    REDIRECT_URI = os.environ['REDIRECT_URI']
    SECRET_KEY = os.environ['SECRET_KEY']
    BOT_TOKEN = os.environ['BOT_TOKEN']
    # L'ID del tuo server di test. Lo convertiamo in un numero intero.
    GUILD_ID = int(os.environ['GUILD_ID'])
except KeyError as e:
    # Se una variabile manca, questo errore apparirà nei log di Render.
    print(f"!!! ERRORE CRITICO: Manca la Environment Variable '{e.args[0]}'. Il programma si fermerà.")
    exit()

API_BASE_URL = 'https://discord.com/api/v10'
# Assicurati che gli "scopes" (permessi) includano 'applications.commands'.
SCOPES = ['identify', 'guilds', 'webhook.incoming', 'applications.commands']


# --- PARTE 1: SITO WEB (FLASK) PER GESTIRE IL LOGIN ---
# Rinominiamo la nostra app Flask per chiarezza.
flask_app = Flask(__name__)
flask_app.secret_key = SECRET_KEY

@flask_app.route('/')
def index():
    if 'access_token' in session:
        return "<h1>Loggato con successo!</h1><p>Ora puoi usare i comandi slash dell'applicazione direttamente dentro Discord.</p>"
    else:
        # Passiamo le variabili al template per costruire il link di login.
        return render_template('index.html', client_id=CLIENT_ID, redirect_uri=REDIRECT_URI, scopes=' '.join(SCOPES))

@flask_app.route('/callback')
def callback():
    # Discord ci rimanda qui dopo che l'utente ha autorizzato l'app.
    code = request.args.get('code')
    
    # Scambiamo il codice temporaneo per un "access token" permanente.
    data = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    r = requests.post(f'{API_BASE_URL}/oauth2/token', data=data, headers=headers)
    
    # Salviamo l'access token nella sessione dell'utente.
    # In un'app reale, questo verrebbe salvato in un database.
    session['access_token'] = r.json()['access_token']
    
    return redirect(url_for('index'))


# --- PARTE 2: BOT DISCORD PER GESTIRE I COMANDI SLASH ---
# Creiamo una classe per il nostro bot per una migliore organizzazione.
class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.default())
        # Questo è l'albero che conterrà i nostri comandi.
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        # Questo metodo viene chiamato quando il bot si avvia.
        # Registra i comandi solo sul nostro server di test per vederli subito.
        test_guild = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=test_guild)
        await self.tree.sync(guild=test_guild)
        print(f"Comandi slash sincronizzati con successo sul server {GUILD_ID}.")

bot = MyBot()

@bot.event
async def on_ready():
    print(f"Bot {bot.user} è online e pronto a ricevere comandi.")

# Definiamo il nostro primo comando slash.
@bot.tree.command(name="raid", description="Invia un certo numero di messaggi in un canale.")
@app_commands.describe(
    messaggio="Il testo da spammare.",
    quantita="Il numero di volte che il messaggio verrà inviato."
)
async def raid_command(interaction: discord.Interaction, messaggio: str, quantita: int):
    # Rispondiamo all'utente con un messaggio che solo lui può vedere.
    await interaction.response.send_message(f"Comando ricevuto! Inizio il raid nel canale {interaction.channel.name}...", ephemeral=True)
    
    try:
        # Creiamo un webhook per mandare messaggi anonimi.
        webhook = await interaction.channel.create_webhook(name="System Message")
    except discord.Forbidden:
        # Se il bot non ha i permessi, lo diciamo all'utente.
        await interaction.followup.send("ERRORE: Non ho il permesso di creare webhook in questo canale.", ephemeral=True)
        return

    # Eseguiamo lo spam.
    for _ in range(quantita):
        await webhook.send(messaggio)
    
    # Cancelliamo il webhook per non lasciare tracce.
    await webhook.delete()
    
    # Diciamo all'utente che abbiamo finito.
    await interaction.followup.send("Raid completato con successo.", ephemeral=True)


# --- PARTE 3: AVVIO COMBINATO DEL SITO E DEL BOT ---
def run_bot_in_thread():
    # Questa funzione fa partire il bot.
    bot.run(BOT_TOKEN)

if __name__ == '__main__':
    # Creiamo un "thread" separato per far girare il bot in background.
    bot_thread = threading.Thread(target=run_bot_in_thread)
    bot_thread.start()
    
    # Esponiamo l'app Flask per Gunicorn.
    # Gunicorn cercherà una variabile chiamata 'app' in questo file.
    # Il nostro start command su Render è `gunicorn main:flask_app`
    # quindi questo alias non è strettamente necessario, ma è una buona pratica.
    app = flask_app 
    
    # NOTA: Gunicorn si occuperà di far partire 'flask_app'. 
    # Non abbiamo bisogno di 'flask_app.run()' qui.
