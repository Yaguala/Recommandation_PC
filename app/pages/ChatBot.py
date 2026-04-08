import streamlit as st
import pandas as pd
import time
#from google import genai
#from google.genai import types
#from google.genai.types import HttpOptions, ModelContent, Part, UserContent
import google.generativeai as genai
from google.generativeai import types
import json # On a besoin de la bibliothèque JSON
from pathlib import Path



import google.generativeai as genai

import streamlit as st
import os
import json


# --------------------------- Bar naviagation ----------------------------------
from streamlit_option_menu import option_menu
with st.container():
    selected = option_menu(
        menu_title=None,
        options=["Home", "Filtre", "ChatBot"],
        icons=[],  # No icons
        default_index=2,
        orientation="horizontal",
        styles={
            "container": {
                "padding": "0!important",
                "background-color": "#da8d00ff",
                "class": "navbar-fixed",  # Add fixed class
            },
            "nav-link": {
                "color": "white",
                "font-size": "16px",
                "margin": "0px",
                "padding": "10px",
            },
            "nav-link-selected": {
                "background-color": "#dfd004ff"
            },
        }
    )
if selected == "Home":
    st.switch_page("app.py")
if selected == "Filtre":
    st.switch_page("pages/filtre.py")
if selected == "ChatBot":
    selected = "ChatBot"
#if selected == "Contact":
#    st.switch_page("pages/Contact.py")
# -----------------------------------------------------------------------------------------------




# Liste de colluns
uploaded_file = Path(__file__).parent.parent / "Data" / "pc_score_cpu_gpu.csv"
df = pd.read_csv(uploaded_file)
Col_liste = list(df.columns)


# --- CERVEAU : Le prompt ultime pour comprendre toutes les intentions ---
def extraire_criteres_de_recherche(user_question, api_key):
    genai.configure(api_key=api_key)
    
    system_prompt_analyzer = """
    Tu es un analyseur de requêtes expert pour un catalogue de PC portables. 
    Ton unique rôle est de traduire la demande de l'utilisateur meme des si necessaire adapter la demande pour du utilisateur (exemple: "utilisetuer: le plus petit", "reponse: taille de ordinateur 14 pounces") en un objet JSON structuré. 
    Ne réponds JAMAIS autre chose que l'objet JSON pur.

    L'objet JSON doit avoir cette structure (toutes les clés sont optionnelles, ne les inclus que si l'utilisateur les mentionne explicitement) :

    {
      "critere_principal": {
        "budget_max": "integer",      // Le prix maximum en euros (ex: 1200)
        "usage": "string",            // Une de ces valeurs : "gaming", "bureautique", "graphisme"
        "marque": "string"            // La marque du PC (ex: "Asus", "HP", "Apple", "Dell", "Lenovo")
        "os": "string"            // NOUVELLE LIGNE : Les valeurs possibles sont "Windows", "macOS", "ChromeOS", ou "Linux"
      },
      "performance": {
        "marque_cpu": "string",       // "Intel" ou "AMD"
        "marque_gpu": "string",       // "NVIDIA", "AMD", ou "Intel"
        "ram_min": "string",         // La RAM minimum en Go (ex: 16, 32)
        "type_disque": "string"       // "SSD" ou "HDD"
      },
      "ecran": {
        "taille_min": "string",        // La taille d'écran minimum en pouces (ex: 15)
        "taux_rafraichissement_min": "integer", // Le taux de rafraîchissement min en Hz (ex: 120, 144)
        "type_dalle": "string",       // "mat" ou "brillant"
        "resolution_specifique": "string" // "QHD", "4K", "Full HD"
      },
      "portabilite_et_design": {
        "poids_max": "string",         // Le poids maximum en kg (ex: 1.5)
        "couleur": "string",          // Couleur spécifique (ex: "noir", "gris", "blanc")
        "materiau": "string"          // Matériau spécifique (ex: "aluminium", "métal")
      }
    }

    Exemples :
    - Question: "Je cherche un PC gamer puissant avec un écran 144Hz, clavier RGB, et un budget de 1800€."
      -> {"critere_principal": {"budget_max": 1800, "usage": "gaming"}, "ecran": {"taux_rafraichissement_min": 144}, "clavier_et_connectique": {"clavier_rgb": true}}
    - Question: "Un ultrabook léger pour le travail, moins de 1.3kg, en aluminium et avec un écran mat."
      -> {"critere_principal": {"usage": "bureautique"}, "portabilite_et_design": {"poids_max": 1.3, "ultrabook": true, "materiau": "aluminium"}, "ecran": {"type_dalle": "mat"}}
    - Question: "Un PC Dell pour faire de la retouche photo avec un bon écran tactile 4K et 1To de SSD."
      -> {"critere_principal": {"marque": "Dell", "usage": "graphisme"}, "performance": {"stockage_min": 1000, "type_disque": "SSD"}, "ecran": {"tactile": true, "resolution_specifique": "4K"}}
    """
    
    model = genai.GenerativeModel('gemini-2.5-flash')
    # ... le reste de la fonction est inchangé
    chat = model.start_chat(history=[
        {'role': 'user', 'parts': [{'text': system_prompt_analyzer}]},
        {'role': 'model', 'parts': [{'text': 'OK.'}]}
    ])
    response = chat.send_message(user_question)
    try:
        json_text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(json_text)
    except (json.JSONDecodeError, AttributeError):
        return {}

# --- MUSCLE : La fonction de filtrage qui gère tous les nouveaux critères ---
def appliquer_filtres_df(df, criteres):
    df_filtre = df.copy()

    # Itération sur chaque catégorie de critères
    if "critere_principal" in criteres:
        cp = criteres["critere_principal"]
        if cp.get("budget_max"): df_filtre = df_filtre[df_filtre['price_float'] <= cp["budget_max"]]
        if cp.get("marque"): df_filtre = df_filtre[df_filtre['Marque'].str.contains(cp["marque"], case=False, na=False)]
        usage = cp.get("usage")
        if usage == "gaming": df_filtre = df_filtre[df_filtre['Gamer'] == True]
        elif usage == "graphisme": df_filtre = df_filtre[df_filtre['Graphisme'] == True]
        elif usage == "bureautique": df_filtre = df_filtre[df_filtre['Bureautique'] == True]
        if cp.get("os"): df_filtre = df_filtre[df_filtre["Système d'exploitation"].str.contains(cp["os"], case=False, na=False)]
        # ... autres usages

    if "performance" in criteres:
        perf = criteres["performance"]
        if perf.get("marque_cpu"): df_filtre = df_filtre[df_filtre['Marque processeur'].str.contains(perf["marque_cpu"], case=False, na=False)]
        if perf.get("marque_gpu"): df_filtre = df_filtre[df_filtre['Chipset graphique'].str.contains(perf["marque_gpu"], case=False, na=False)]
        if perf.get("ram_min"): df_filtre = df_filtre[df_filtre['Taille de la mémoire'].str.contains(perf["ram_min"], case=False, na=False)]
        if perf.get("stockage_min"): df_filtre = df_filtre[df_filtre['Capacité'] >= perf["stockage_min"]]
        if perf.get("type_disque"): df_filtre = df_filtre[df_filtre['Type de Disque'].str.contains(perf["type_disque"], case=False, na=False)]

    if "ecran" in criteres:
        ecran = criteres["ecran"]
        if ecran.get("taille_min"): df_filtre = df_filtre[df_filtre["Taille de l'écran"].str.contains(ecran["taille_min"])]
        if ecran.get("tactile"): df_filtre = df_filtre[df_filtre['Ecran tactile'] == True]
        if ecran.get("taux_rafraichissement_min"): df_filtre = df_filtre[df_filtre['Taux de rafraîchissement'] >= ecran["taux_rafraichissement_min"]]
        if ecran.get("type_dalle") == "mat": df_filtre = df_filtre[df_filtre['Dalle mate/antireflets'] == True]
        if ecran.get("type_dalle") == "brillant": df_filtre = df_filtre[df_filtre['Dalle brillante'] == True]
        if ecran.get("resolution_specifique"): df_filtre = df_filtre[df_filtre['Résolution Max'].str.contains(ecran["resolution_specifique"], case=False, na=False)]

    if "portabilite_et_design" in criteres:
        port = criteres["portabilite_et_design"]
        if port.get("poids_max"): df_filtre = df_filtre[df_filtre['Poids'] <= port["poids_max"]]
        if port.get("ultrabook"): df_filtre = df_filtre[df_filtre['Ultrabook'] == True]
        if port.get("couleur"): df_filtre = df_filtre[df_filtre['Couleur'].str.contains(port["couleur"], case=False, na=False)]
        if port.get("materiau"): df_filtre = df_filtre[df_filtre['Matériau'].str.contains(port["materiau"], case=False, na=False)]

    if "clavier_et_connectique" in criteres:
        clav = criteres["clavier_et_connectique"]
        if clav.get("clavier_retroeclaire"): df_filtre = df_filtre[df_filtre['Clavier rétroéclairé'] == True]
        if clav.get("clavier_rgb"): df_filtre = df_filtre[df_filtre['Clavier RGB'] == True]
        if clav.get("pave_numerique"): df_filtre = df_filtre[df_filtre['Pavé numérique'] == True]
        if clav.get("charge_usb_c"): df_filtre = df_filtre[df_filtre['Charge de la batterie par USB-C'] == True]
        
    return df_filtre

# --- FONCTION PRINCIPALE DE LA PAGE ---
def show_chatbot_page():
    st.divider()
    right,mid, left = st.columns([1,5,1])
    mid.title("Le spécialiste de la Tech")
    mid.markdown("Bienvenue ! Posez-moi vos questions sur les ordinateurs portables.")

    uploaded_file = Path(__file__).parent.parent / "Data" / "pc_score_cpu_gpu.csv"

    if uploaded_file is not None:
        # On charge le DataFrame une seule fois et on le met en cache Streamlit
        @st.cache_data
        def load_data(path):
            return pd.read_csv(path)

        df = load_data(uploaded_file)
        # Custom CSS for the text area
        st.markdown("""
            <style>
            textarea {
                border: 3px solid #dfd004ff !important;
                border-radius: 6px !important;
                box-shadow: none !important;
                padding: 10px !important;
                font-size: 16px !important;
            }
            </style>
        """, unsafe_allow_html=True)
        
        # ==================== API KEY POR SESSÃO ====================
        if "api_key" not in st.session_state:
            st.session_state.api_key = None

        # ==================== INPUT NO MEIO DA PÁGINA ====================
        if not st.session_state.api_key:
            st.markdown("""
                        ## Pour utiliser le chatbot, vous devez fournir votre propre **clé API Gemini**.
                        
                        **Comment utiliser votre clé API ?**

                        1. Allez sur [Google AI Studio](https://aistudio.google.com/app/apikey)  
                        2. Créez une nouvelle clé API (gratuit)  
                        3. Copiez-la  
                        4. Collez-la dans le champ ci-dessous  
                        5. Cliquez sur **"Utiliser cette clé"**

                        Votre clé sera **utilisée uniquement pendant cette session**.  
                        Elle disparaîtra automatiquement quand vous fermerez l’onglet ou la page.
                        """)
            if st.session_state.api_key:
                st.success("Clé configurée pour cette session")
                if st.button("Modifier / Supprimer la clé"):
                    st.session_state.api_key = None
                    st.rerun()
            else:
                key_input = st.text_input("Collez votre clé API ici :", type="password")
                if st.button("Utilisez cette clé"):
                    if key_input.strip():
                        st.session_state.api_key = key_input.strip()
                        st.success("Clé enregistrée pour cette session !")
                        st.rerun()
                    else:
                        st.error("La clé ne peut pas être vide.")

        # ==================== USO NO RESTO DO APP ====================
        api_key = st.session_state.api_key

        if not api_key:
            st.warning("Saisissez votre clé API ci-dessus pour utiliser l'application.")
            st.stop()

        
        st.write("Clé API chargée avec succès !")

        # ------------------------ Chat Bot ---------------------------
        
        user_question = st.text_area("Votre question : ", height=100, placeholder="Ex: Je cherche un PC pour le gaming avec un budget de 1500€")

        if st.button("Poser la question", help="Cliquez pour obtenir une réponse"):
            if user_question:
                with st.spinner("Analyse de votre demande..."):
                    criteres = extraire_criteres_de_recherche(user_question, api_key)
                    #st.write("Critères détectés :", criteres) # Ligne de debug, à enlever plus tard

                    # --- ÉTAPE 2 : Filtrer le DataFrame --
                    df_filtre = appliquer_filtres_df(df, criteres)

                # --- ÉTAPE 3 : Envoyer les données filtrées au Chatbot ---
                if df_filtre.empty:
                    st.warning("Désolé, aucun ordinateur ne correspond à vos critères dans ma base de données.")
                else:
                    with st.spinner("Je cherche la meilleure recommandation parmi les PC correspondants..."):
                        # On convertit le PETIT dataframe en CSV
                        csv_data_filtre = df_filtre.head(150).to_csv(index=False)
                        
                        # On prépare le prompt final
                        system_prompt_final = f"""Tu es un expert en PC portables. Réponds à la question de l'utilisateur en te basant UNIQUEMENT sur la liste de PC suivante. 
                        Ne propose rien qui ne soit pas dans cette liste.
                        --- LISTE DE PC PERTINENTS ---
                        {csv_data_filtre}
                        --- FIN DE LA LISTE ---
                        
                        La question de l'utilisateur est : "{user_question}"
                        
                        Fournis le lien Streamlit 'http://localhost:8501/Filtre?pc=' suivi de l'numero dans la column index pour chaque PC que tu sugeres.
                        Explique ton choix en détail.
                        Ta une limite de sugestion de 5 PC

                        Exemple de reponse:
                        1. AORUS 16X 9KG-43FRC54SH // Text en Negrite // : http://localhost:8501/Filtre?pc=34 /n
                        Detail de choix:  // Limite a 60 Tokens Ne afiche pas le "Detail de choix:"
                
                        """
                        
                    with st.spinner("Je cherche la meilleure recommandation..."):
                        genai.configure(api_key=api_key)
                        model = genai.GenerativeModel('gemini-2.5-flash')
                        response_stream = model.generate_content(
                            system_prompt_final, 
                            stream=True,
                            generation_config=types.GenerationConfig(max_output_tokens=8192)
                        )
                        
                        # --- LA CORRECTION FINALE EST ICI ---
                        # On parcourt manuellement le stream et on affiche le texte
                        st.subheader("Ma recommandation pour vous :")
                        full_response = ""
                        placeholder = st.empty()
                        for chunk in response_stream:
                            # Assurez-vous que chunk.text n'est pas None
                            if chunk.text:
                                full_response += chunk.text
                                placeholder.markdown(full_response + "▌")
                        placeholder.markdown(full_response)
                        # --- FIN DE LA CORRECTION ---

    else:
        st.error("Impossible de charger le fichier CSV.")

# ... (le reste de votre code est correct)
if 'selected' in locals() and selected == "ChatBot":
    show_chatbot_page()