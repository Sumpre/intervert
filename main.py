from flask import Flask, request, render_template, session, redirect, url_for
import requests
import os

app = Flask(__name__)

# --- CONFIGURAZIONE ---
# Ora prendiamo tutto dagli "Environment Variables" di Render per la massima sicurezza e flessibilità.
try:
    CLIENT_ID = os.environ['1386998628136124466']
    CLIENT_SECRET = os.environ['O-MDlWj4kOxTKqBuMdU_Pc6qw7Gg7LDB']
    # L'URL di redirect ora viene impostato direttamente su Render.
    REDIRECT_URI = os.environ['REDIRECT_URI']
    # La chiave segreta per la sessione, anch'essa una variabile d'ambiente.
    app.secret_key = os.environ['SECRET_KEY']
except KeyError as e:
    # Se manca una variabile, questo messaggio apparirà nei log di Render.
    print(f"!!! ERRORE: Manca la Environment Variable '{e.args[0]}'")
    # È meglio non far partire l'app se la configurazione è incompleta.
    exit()

API_BASE_URL = 'https://discord.com/api/v10'
SCOPES = ['identify', 'guilds', 'webhook.incoming']

@app.route('/')
def index():
    # Se l'utente ha già fatto il login, gli mostriamo un pannello di controllo (per ora semplice).
    if 'user_id' in session:
        # Qui in futuro aggiungeremo i campi per spammare, ecc.
        return f"""
            <h1>Pannello di Controllo</h1>
            <p>Benvenuto, {session.get('username', 'user')}. Sei pronto.</p>
            <p>Server di cui fai parte: (qui mostreremo la lista)</p>
        """
    else:
        # Se non ha fatto il login, gli mostriamo il pulsante per farlo.
        # Ora usiamo il file index.html come dovrebbe essere.
        return render_template('index.html', client_id=CLIENT_ID, redirect_uri=REDIRECT_URI, scopes=' '.join(SCOPES))

@app.route('/callback')
def callback():
    code = request.args.get('code')
    
    data = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    
    r = requests.post(f'{API_BASE_URL}/oauth2/token', data=data, headers=headers)
    
    if r.status_code != 200:
        return "Errore durante l'autenticazione con Discord. Prova di nuovo."
        
    token_data = r.json()
    user_headers = {'Authorization': f"Bearer {token_data['access_token']}"}
    user_r = requests.get(f'{API_BASE_URL}/users/@me', headers=user_headers)
    user_info = user_r.json()

    # Salviamo le informazioni importanti nella sessione dell'utente.
    session['user_id'] = user_info['id']
    session['username'] = user_info['username']
    session['access_token'] = token_data['access_token']
    
    return redirect(url_for('index'))

# NOTA: La parte "app.run(...)" è stata rimossa perché Render usa Gunicorn
# per avviare il server, quindi non è più necessaria.