import streamlit as st


# --------------------------- Bar naviagation ----------------------------------
from streamlit_option_menu import option_menu
with st.container():
    selected = option_menu(
        menu_title=None,
        options=["Home", "Filtre", "ChatBot"],
        icons=[],  # No icons
        default_index=1,
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
    st.session_state.selected_pc = None
    st.query_params.clear()
    st.switch_page("app.py")
if selected == "Filtre":
    selected =  "Filtre"
if selected == "ChatBot":
    st.session_state.selected_pc = None
    st.query_params.clear()
    st.switch_page("pages/Chatbot.py")
#if selected == "Contact":
#    st.switch_page("pages/Contact.py")
# -----------------------------------------------------------------------------------------------



# ─── Config ───

def show_filtre_page():
    import pandas as pd
    import numpy as np
    from pathlib import Path
    #import Data
    
    
    # ─── Data ───
    csv_path = Path(__file__).parent.parent / "data" / "pc_score_cpu_gpu.csv"
    df = pd.read_csv(csv_path)

    req = {"img_url", "Désignation", "Bureautique", "Gamer", "Graphisme"}
    if not req.issubset(df.columns):
        st.error(f"Colonnes manquantes : {', '.join(req - set(df.columns))}")
        st.stop()

    if "selected_type" not in st.session_state:
        st.session_state.selected_type = None
    if "selected_pc" not in st.session_state:
        st.session_state.selected_pc = None

    query_params = st.query_params
    if "pc" in query_params:
        try:
            pc_idx = int(query_params["pc"])
            if 0 <= pc_idx < len(df):
                st.session_state.selected_pc = pc_idx
        except:
            pass

    def show_pc_list():
        st.title("Trouve le PC adapté à tes besoins")

        st.markdown("""
        <style>
        div.stButton > button {width:100%; height:90px; font-size:1.2rem; border-radius:12px;}
        </style>
        """, unsafe_allow_html=True)

        types = ["Bureautique", "Gamer", "Graphisme"]
        btn_cols = st.columns(3)
        for i, act in enumerate(types):
            with btn_cols[i % 3]:
                if st.button(act, key=f"btn_{i}"):
                    st.session_state.selected_type = act
                    st.session_state.selected_pc = None
                    st.query_params.clear()
        if not st.session_state.selected_type:
            st.warning("Veuillez sélectionner une catégorie pour voir les résultats.")
            return

        filtered = df[df[st.session_state.selected_type] == 1]

        st.sidebar.header("Filtres avancés")

        SLIDER_COLS = ["3d_mark", "geekbench", "price", "Epaisseur", "Profondeur", "Largeur", "Poids", "Autonomie"]

        filter_cols = [
            "Processeur", "GPU series", "Type d'écran", "Type de Dalle", "Clavier rétroéclairé", "Technologie Bluetooth",
            "Fréquence CPU", "Nombre de core", "Taille de la mémoire", "Capacité", "Taille de l'écran",
            "Résolution Max", "Taux de rafrâchissement",
            "CPU_benchmark_single_core", "CPU_benchmark_multi_core",
            "3d_mark", "geekbench", "price", "Epaisseur", "Profondeur", "Largeur", "Poids", "Autonomie"
        ]
        filter_cols = [col for col in filter_cols if col in filtered.columns]

        for col in filter_cols:
            col_clean = filtered[col].dropna()
            if col_clean.empty:
                continue
            if np.issubdtype(col_clean.dtype, np.number) and col in SLIDER_COLS:
                mn, mx = float(col_clean.min()), float(col_clean.max())
                low, high = st.sidebar.slider(col, mn, mx, (mn, mx))
                filtered = filtered[(filtered[col] >= low) & (filtered[col] <= high)]
            elif col_clean.dtype == object or col_clean.nunique() <= 20:
                opts = sorted(col_clean.unique())
                selected = st.sidebar.multiselect(col, opts)
                if selected:
                    filtered = filtered[filtered[col].isin(selected)]

        if filtered.empty:
            st.warning("Aucun PC ne correspond aux filtres sélectionnés.")
            return

        st.caption(f"{len(filtered)} PC trouvé(s)")
        img_cols = st.columns(4)
        for idx, row in filtered.reset_index().iterrows():
            with img_cols[idx % 4]:
                pc_index = row["index"]
                label = str(row["Désignation"]) if pd.notna(row["Désignation"]) else "Sans nom"
                st.markdown(
                    f"<div style='text-align:center; font-size:1.2rem; font-weight:500; margin-bottom:0.5rem'>{label}</div>",
                    unsafe_allow_html=True
                )
                img_html = f"""
                <a href="?pc={pc_index}" target="_self"> 
                    <img src="{row['img_url']}" style="width:100%; border-radius:8px;
                        box-shadow: 0px 8px 18px rgba(0,0,0,0.5);" />
                </a>
                """
                st.markdown(img_html, unsafe_allow_html=True)

    def show_pc_details():
        pc = df.loc[st.session_state.selected_pc]
        cols = st.columns([5, 1])
        with cols[1]:
            if st.button("← Retour"):
                st.session_state.selected_pc = None
                st.query_params.clear()

        st.title(pc["Désignation"] if pd.notna(pc["Désignation"]) else "Fiche PC")
        st.markdown("---")
        col_img, col_info = st.columns([1, 4])
        with col_img:
            st.image(pc["img_url"], width=250)
        with col_info:
            st.markdown("### Résumé technique")
            def icon_text(icon, text):
                return f"{icon}  {text}"
            lines = []
            if pd.notna(pc.get("Processeur")):
                lines.append(icon_text("🧠 CPU:", pc["Processeur"]))
            if pd.notna(pc.get("Nombre de core")):
                lines.append(icon_text("⚙️ Cœurs:", pc["Nombre de core"]))
            if pd.notna(pc.get("Taille de la mémoire")):
                lines.append(icon_text("💾 RAM:", f"{pc['Taille de la mémoire']} Go"))
            if pd.notna(pc.get("GPU series")):
                lines.append(icon_text("🎮 GPU:", pc["GPU series"]))
            if pd.notna(pc.get("Taille de l'écran")):
                screen_size = pc['Taille de l\'écran']
                lines.append(icon_text("💥 Écran:", f"{screen_size}"))
            if pd.notna(pc.get("3d_mark")):
                lines.append(icon_text("📊 3D Mark:", str(pc["3d_mark"])))
            st.markdown("<br>".join(lines), unsafe_allow_html=True)

            st.markdown("#### 💰 Prix")
            price = pc.get("price")
            if pd.notna(price):
                try:
                    price_str = str(price).replace("€", "").replace(" ", "").replace("\u202f", "")
                    if price_str[-2:].isdigit():
                        price_float = float(price_str[:-2] + "." + price_str[-2:])
                        st.success(f"{price_float:,.2f} €".replace(",", " ").replace(".00", ""))
                    else:
                        st.info(f"Prix : {price}")
                except:
                    st.info(f"Prix : {price}")
            else:
                st.info("Prix non renseigné")

        st.markdown("---")
        col_left, col_right = st.columns(2)
        with col_left:
            st.subheader("💡 Performances")
            for key in ["CPU_benchmark_single_core", "CPU_benchmark_multi_core", "geekbench"]:
                if key in pc and pd.notna(pc[key]):
                    st.write(f"**{key} :** {pc[key]}")
            st.subheader("📦 Stockage & Batterie")
            for key in ["Type de Disque", "Capacité", "Nombre de disques", "Autonomie", "Capacité de la batterie"]:
                if key in pc and pd.notna(pc[key]):
                    st.write(f"**{key} :** {pc[key]}")
        with col_right:
            st.subheader("🔌 Connectivité & Extras")
            for key in ["Connecteur(s) disponible(s)", "Type d'écran", "Type de Dalle", "Ecran tactile",
                        "Clavier rétroéclairé", "Clavier RGB", "Lecteur biométrique", "Webcam", "Office fourni",
                        "Norme(s) réseau sans-fil", "Technologie Bluetooth"]:
                if key in pc and pd.notna(pc[key]):
                    st.write(f"**{key} :** {pc[key]}")

    # ─── Navigation ───
    if st.session_state.selected_pc is None:
        show_pc_list()
    else:
        show_pc_details()

if __name__ == "__main__":
    show_filtre_page()
