import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import date
import matplotlib.pyplot as plt
import altair as alt
import numpy as np
from gspread.exceptions import WorksheetNotFound

# --- STYLIZACJA CSS ---
def local_css():
    st.markdown("""
    <style>
        html, body, [class*="css"] { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; }
        .block-container { padding-top: 1rem !important; padding-bottom: 2rem !important; }
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        h1 { color: #8B4513; text-align: center; font-weight: 1000; margin-bottom: 0px; }
        h2 { color: #1B4D3E; border-bottom: 2px solid #FFFFFF; padding-bottom: 10px; }
        [data-testid="stMetric"] {
            background-color: #262730 !important;
            border: 1px solid #444;
            padding: 15px;
            border-radius: 10px;
            box-shadow: 2px 2px 10px rgba(0,0,0,0.5);
            text-align: left;
            margin-bottom: 10px;
        }
        [data-testid="stDataEditor"] {
            border: 1px solid #444 !important;
            border-radius: 10px;
            background-color: #262730;
        }
        [data-testid="stMetricLabel"] { color: white !important; }
        [data-testid="stMetricValue"] { color: #4CAF50 !important; }
        button[data-baseweb="tab"] { font-size: 18px !important; font-weight: 600 !important; }
        button[data-baseweb="tab"][aria-selected="true"] { color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Menadżer Ślubny", page_icon="💍", layout="wide")
local_css()

# --- STAŁE ---
KOLUMNY_GOSCIE   = ["Imie_Nazwisko", "Imie_Osoby_Tow", "RSVP", "Zaproszenie_Wyslane"]
KOLUMNY_OBSLUGA  = ["Kategoria", "Rola", "Informacje", "Koszt", "Czy_Oplacone", "Zaliczka", "Czy_Zaliczka_Oplacona"]
KOLUMNY_ZADANIA  = ["Zadanie", "Termin", "Czy_Zrobione"]
KOLUMNY_STOLY    = ["Numer", "Ksztalt", "Liczba_Miejsc", "Goscie_Lista"]

# --- POŁĄCZENIE Z GOOGLE SHEETS I CACHE'OWANIE ARKUSZY ---
@st.cache_resource
def pobierz_arkusze():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)

    try:
        sh = client.open("Wesele_Baza")
    except Exception:
        st.error("⚠️ Nie znaleziono arkusza 'Wesele_Baza'.")
        st.stop()

    arkusze = {}
    try:
        arkusze["Goscie"] = sh.worksheet("Goscie")
    except WorksheetNotFound:
        st.error("⚠️ Brak zakładki 'Goscie'. Utwórz ją z nagłówkami: Imie_Nazwisko, Imie_Osoby_Tow, RSVP, Zaproszenie_Wyslane.")
        st.stop()
    try:
        arkusze["Obsluga"] = sh.worksheet("Obsluga")
    except WorksheetNotFound:
        st.error("⚠️ Brak zakładki 'Obsluga'. Utwórz ją z nagłówkami: Kategoria, Rola, Informacje, Koszt, Czy_Oplacone, Zaliczka, Czy_Zaliczka_Oplacona.")
        st.stop()
    try:
        arkusze["Zadania"] = sh.worksheet("Zadania")
    except WorksheetNotFound:
        arkusze["Zadania"] = None
        st.warning("⚠️ Brak zakładki 'Zadania' – lista zadań nie będzie działać.")
    try:
        arkusze["Stoly"] = sh.worksheet("Stoly")
    except WorksheetNotFound:
        arkusze["Stoly"] = None
        st.warning("⚠️ Brak zakładki 'Stoly' – plan stołów nie będzie działać.")
    return arkusze

arkusze = pobierz_arkusze()
worksheet_goscie  = arkusze["Goscie"]
worksheet_obsluga = arkusze["Obsluga"]
worksheet_zadania = arkusze["Zadania"]
worksheet_stoly   = arkusze["Stoly"]

# --- FUNKCJE POMOCNICZE ---
def pobierz_dane(_worksheet):
    return pd.DataFrame(_worksheet.get_all_records())

def zapisz_nowy_wiersz(worksheet, lista_wartosci):
    worksheet.append_row(lista_wartosci)
    st.cache_data.clear()

def aktualizuj_caly_arkusz(worksheet, df):
    worksheet.clear()
    worksheet.update([df.columns.values.tolist()] + df.values.tolist())
    st.cache_data.clear()

# --- FUNKCJE ŁADUJĄCE DANE (tylko raz) ---
def load_goscie():
    if worksheet_goscie is None:
        return pd.DataFrame(columns=KOLUMNY_GOSCIE)
    df = pobierz_dane(worksheet_goscie)
    if df.empty:
        df = pd.DataFrame(columns=KOLUMNY_GOSCIE)
    df["RSVP"] = df["RSVP"].apply(lambda x: str(x).lower() in ["tak", "true", "1", "yes"])
    df["Zaproszenie_Wyslane"] = df["Zaproszenie_Wyslane"].apply(lambda x: str(x).lower() in ["tak", "true", "1", "yes"])
    df = df.fillna("")
    return df

def load_obsluga():
    if worksheet_obsluga is None:
        return pd.DataFrame(columns=KOLUMNY_OBSLUGA)
    df = pobierz_dane(worksheet_obsluga)
    if 'ID' in df.columns:
        df = df.drop(columns=['ID'])
    if df.empty:
        df = pd.DataFrame(columns=KOLUMNY_OBSLUGA)
    df["Koszt"] = pd.to_numeric(df["Koszt"], errors='coerce').fillna(0.0)
    df["Zaliczka"] = pd.to_numeric(df["Zaliczka"], errors='coerce').fillna(0.0)
    df["Czy_Oplacone"] = df["Czy_Oplacone"].apply(lambda x: str(x).lower() in ["tak", "true", "1", "yes"])
    df["Czy_Zaliczka_Oplacona"] = df["Czy_Zaliczka_Oplacona"].apply(lambda x: str(x).lower() in ["tak", "true", "1", "yes"])
    df = df.fillna("")
    return df

def load_zadania():
    if worksheet_zadania is None:
        return pd.DataFrame(columns=KOLUMNY_ZADANIA)
    df = pobierz_dane(worksheet_zadania)
    if df.empty:
        df = pd.DataFrame(columns=KOLUMNY_ZADANIA)
    df["Termin"] = pd.to_datetime(df["Termin"], errors='coerce').dt.date
    df["Czy_Zrobione"] = df["Czy_Zrobione"].apply(lambda x: str(x).lower() in ["tak", "true", "1", "yes"])
    df = df.fillna("")
    return df

def load_stoly():
    if worksheet_stoly is None:
        return pd.DataFrame(columns=KOLUMNY_STOLY)
    df = pobierz_dane(worksheet_stoly)
    if df.empty:
        df = pd.DataFrame(columns=KOLUMNY_STOLY)
    df["Numer"] = df["Numer"].astype(str)
    df["Liczba_Miejsc"] = pd.to_numeric(df["Liczba_Miejsc"], errors='coerce').fillna(0).astype(int)
    df = df.fillna("")
    return df

# --- UI APLIKACJI ---
st.title("💍 Menadżer Ślubny")
tab1, tab2, tab3, tab4 = st.tabs(["👥 Lista Gości", "🎧 Organizacja", "✅ Lista Zadań", "🍽️ Rozplanowanie Stołów"])

# ==========================
# ZAKŁADKA 1: GOŚCIE
# ==========================
with tab1:
    st.header("👥 Zarządzanie Gośćmi")
    
    if "df_goscie" not in st.session_state:
        st.session_state["df_goscie"] = load_goscie()
    df_goscie = st.session_state["df_goscie"]

    def obsluga_dodawania():
        imie_glowne = st.session_state.get("input_imie", "")
        imie_partnera = st.session_state.get("input_partner", "")
        czy_rsvp = st.session_state.get("check_rsvp", False)
        czy_z_osoba = st.session_state.get("check_plusone", False)
        czy_zaproszenie = st.session_state.get("check_invite", False)

        if imie_glowne:
            nowe_wiersze = []
            nowe_wiersze.append([imie_glowne, "", czy_rsvp, czy_zaproszenie])
            if czy_z_osoba and imie_partnera:
                nowe_wiersze.append([imie_partnera, f"(Osoba tow. dla: {imie_glowne})", czy_rsvp, czy_zaproszenie])

            # Aktualizacja session_state
            df = st.session_state["df_goscie"].copy()
            for w in nowe_wiersze:
                nowy = dict(zip(KOLUMNY_GOSCIE, w))
                df = pd.concat([df, pd.DataFrame([nowy])], ignore_index=True)
            st.session_state["df_goscie"] = df

            # Zapis do arkusza
            for w in nowe_wiersze:
                w_arkusz = w.copy()
                w_arkusz[2] = "Tak" if w_arkusz[2] else "Nie"
                w_arkusz[3] = "Tak" if w_arkusz[3] else "Nie"
                zapisz_nowy_wiersz(worksheet_goscie, w_arkusz)

            st.toast(f"✅ Dodano: {imie_glowne}")
            # Czyszczenie pól
            st.session_state["input_imie"] = ""
            st.session_state["input_partner"] = ""
            st.session_state["check_rsvp"] = False
            st.session_state["check_plusone"] = False
            st.session_state["check_invite"] = False
        else:
            st.warning("Musisz wpisać imię głównego gościa!")

    with st.expander("➕ Szybkie dodawanie (Formularz)", expanded=False):
        czy_z_osoba = st.checkbox("Chcę dodać też osobę towarzyszącą (+1)", key="check_plusone")
        c1, c2 = st.columns(2)
        with c1:
            st.text_input("Imię i Nazwisko Gościa", key="input_imie")
        with c2:
            if czy_z_osoba:
                st.text_input("Imię Osoby Towarzyszącej", key="input_partner")
        k1, k2 = st.columns(2)
        with k1:
            st.checkbox("✉️ Zaproszenie wysłane?", key="check_invite")
        with k2:
            st.checkbox("✅ Potwierdzenie Przybycia", key="check_rsvp")
        st.button("Dodaj do listy", on_click=obsluga_dodawania, key="btn_goscie")

    st.write("---")
    st.subheader(f"📋 Lista Gości ({len(df_goscie)} pozycji)")

    df_display = df_goscie.copy()
    df_display["Imie_Nazwisko"] = df_display["Imie_Nazwisko"].astype(str).replace("nan", "")
    df_display["Imie_Osoby_Tow"] = df_display["Imie_Osoby_Tow"].astype(str).replace("nan", "")

    col_sort1, col_sort2 = st.columns([1, 3])
    with col_sort1:
        st.write("**Sortuj wg:**")
    with col_sort2:
        tryb_sortowania = st.radio(
            "Wybierz tryb sortowania",
            options=["Domyślnie", "✉️ Wysłane zaproszenia", "✉️ Brak zaproszenia", "✅ Potwierdzone Przybycie", "🔤 Nazwisko (A-Z)"],
            label_visibility="collapsed",
            horizontal=True,
            key="sort_goscie_radio"
        )

    if tryb_sortowania == "✉️ Wysłane zaproszenia":
        df_display = df_display.sort_values(by="Zaproszenie_Wyslane", ascending=False)
    elif tryb_sortowania == "✉️ Brak zaproszenia":
        df_display = df_display.sort_values(by="Zaproszenie_Wyslane", ascending=True)
    elif tryb_sortowania == "✅ Potwierdzone Przybycie":
        df_display = df_display.sort_values(by="RSVP", ascending=False)
    elif tryb_sortowania == "🔤 Nazwisko (A-Z)":
        df_display = df_display.sort_values(by="Imie_Nazwisko", ascending=True)

    edytowane_goscie = st.data_editor(
        df_display,
        num_rows="dynamic",
        column_config={
            "Imie_Nazwisko": st.column_config.TextColumn("Imię i Nazwisko", required=True),
            "Imie_Osoby_Tow": st.column_config.TextColumn("Info (+1) / Powiązanie", width="large"),
            "Zaproszenie_Wyslane": st.column_config.CheckboxColumn("✉️ Wysłane Zaproszenie", default=False),
            "RSVP": st.column_config.CheckboxColumn("✅ Potwierdzone Przybycie", default=False)
        },
        use_container_width=True,
        hide_index=True,
        key="editor_goscie"
    )

    if st.button("💾 Zapisz zmiany", key="save_goscie"):
        df_to_save = edytowane_goscie.copy()
        df_to_save = df_to_save[df_to_save["Imie_Nazwisko"].str.strip() != ""]

        df_arkusz = df_to_save.copy()
        df_arkusz["RSVP"] = df_arkusz["RSVP"].apply(lambda x: "Tak" if x else "Nie")
        df_arkusz["Zaproszenie_Wyslane"] = df_arkusz["Zaproszenie_Wyslane"].apply(lambda x: "Tak" if x else "Nie")
        df_arkusz = df_arkusz.fillna("")
        aktualizuj_caly_arkusz(worksheet_goscie, df_arkusz)

        st.session_state["df_goscie"] = df_to_save
        st.success("Zapisano zmiany!")
        st.rerun()

    # Statystyki
    if not df_goscie.empty:
        potwierdzone = len(df_goscie[df_goscie["RSVP"] == True])
        zaproszone = len(df_goscie[df_goscie["Zaproszenie_Wyslane"] == True])
        total_goscie = len(df_goscie)
        st.write("---")
        card_style = "background-color: #262730; border: 1px solid #444; padding: 15px; border-radius: 10px; box-shadow: 2px 2px 10px rgba(0,0,0,0.5); text-align: left; margin-bottom: 10px;"
        k1, k2, k3 = st.columns(3)
        k1.markdown(f'<div style="{card_style}"><div style="color: #F5F5DC; font-size: 14px; margin-bottom: 5px;">Liczba gości</div><div style="color: #4CAF50; font-size: 30px; font-weight: 700;">{total_goscie}</div></div>', unsafe_allow_html=True)
        k2.markdown(f'<div style="{card_style}"><div style="color: #F5F5DC; font-size: 14px; margin-bottom: 5px;">Wysłane zaproszenia</div><div style="color: #4CAF50; font-size: 30px; font-weight: 700;">{zaproszone}</div></div>', unsafe_allow_html=True)
        k3.markdown(f'<div style="{card_style}"><div style="color: #F5F5DC; font-size: 14px; margin-bottom: 5px;">Potwierdzone przybycia</div><div style="color: #4CAF50; font-size: 30px; font-weight: 700;">{potwierdzone}</div></div>', unsafe_allow_html=True)

# ==========================
# ZAKŁADKA 2: ORGANIZACJA (w pełni edytowalna tabela)
# ==========================
with tab2:
    st.header("🎧 Organizacja i Budżet")
    
    if "df_obsluga" not in st.session_state:
        st.session_state["df_obsluga"] = load_obsluga()
    df_obsluga = st.session_state["df_obsluga"]

    # Lista kategorii do selectboksów
    base_cats = ["Inne"]
    if not df_obsluga.empty:
        curr = df_obsluga["Kategoria"].unique().tolist()
        all_cats = sorted(list(set(base_cats + [x for x in curr if str(x).strip() != ""])))
    else:
        all_cats = sorted(base_cats)
    select_opts = all_cats + ["➕ Stwórz nową..."]

    def dodaj_usluge():
        sel = st.session_state.get("org_k_sel")
        inp = st.session_state.get("org_k_inp", "")
        fin_cat = inp.strip() if sel == "➕ Stwórz nową..." else sel
        r = st.session_state.get("org_rola", "")
        i = st.session_state.get("org_info", "")
        k = st.session_state.get("org_koszt", 0.0)
        op = st.session_state.get("org_op", False)
        z = st.session_state.get("org_zal", 0.0)
        z_op = st.session_state.get("org_z_op", False)

        if r and fin_cat:
            nowy_wiersz = [fin_cat, r, i, k, op, z, z_op]
            # Aktualizacja session_state
            df = st.session_state["df_obsluga"].copy()
            nowy = dict(zip(KOLUMNY_OBSLUGA, nowy_wiersz))
            df = pd.concat([df, pd.DataFrame([nowy])], ignore_index=True)
            st.session_state["df_obsluga"] = df

            # Zapis do arkusza
            w_arkusz = nowy_wiersz.copy()
            w_arkusz[4] = "Tak" if w_arkusz[4] else "Nie"
            w_arkusz[6] = "Tak" if w_arkusz[6] else "Nie"
            zapisz_nowy_wiersz(worksheet_obsluga, w_arkusz)

            st.toast(f"💰 Dodano: {r}")
            # Czyszczenie pól
            st.session_state["org_rola"] = ""
            st.session_state["org_info"] = ""
            st.session_state["org_koszt"] = 0.0
            st.session_state["org_op"] = False
            st.session_state["org_zal"] = 0.0
            st.session_state["org_z_op"] = False
            st.session_state["org_k_inp"] = ""
        else:
            st.warning("Wpisz Rolę i Kategorię")

    with st.expander("➕ Dodaj koszt", expanded=False):
        c_select, c_input = st.columns(2)
        with c_select:
            sel = st.selectbox("Kategoria", select_opts, key="org_k_sel")
        with c_input:
            if sel == "➕ Stwórz nową...":
                st.text_input("Nowa nazwa:", key="org_k_inp")
        st.text_input("Rola", key="org_rola", placeholder="np. DJ, Florystka")
        c1, c2 = st.columns(2)
        with c1:
            st.number_input("Koszt Całkowity (zł)", step=100.0, key="org_koszt")
            st.checkbox("Całość opłacona?", key="org_op")
        with c2:
            st.number_input("Zaliczka (zł)", step=100.0, key="org_zal")
            st.checkbox("Zaliczka opłacona?", key="org_z_op")
        st.text_input("Informacje dodatkowe", key="org_info", placeholder="Kontakt, termin płatności...")
        st.button("Dodaj", on_click=dodaj_usluge, key="btn_org")

    st.write("---")
    st.subheader(f"💸 Wydatki ({len(df_obsluga)})")

    # Filtrowanie
    fil = st.multiselect("🔍 Filtruj:", all_cats)
    df_disp = df_obsluga.copy()
    if fil:
        df_disp = df_disp[df_disp["Kategoria"].isin(fil)]

    # Sortowanie
    c1, c2 = st.columns([1,3])
    with c1:
        st.write("Sortuj:")
    with c2:
        s = st.radio("S", ["Domyślnie", "💰 Najdroższe", "❌ Nieopłacone", "✅ Opłacone"], horizontal=True, label_visibility="collapsed", key="sort_org")
    if s == "💰 Najdroższe":
        df_disp = df_disp.sort_values("Koszt", ascending=False)
    elif s == "❌ Nieopłacone":
        df_disp = df_disp.sort_values("Czy_Oplacone", ascending=True)
    elif s == "✅ Opłacone":
        df_disp = df_disp.sort_values("Czy_Oplacone", ascending=False)

    # EDYTOR DANYCH – pełna edycja, dynamiczne wiersze
    # ProgressColumn ZOSTAŁ USUNIĘTY – Koszt to zwykła liczba
    edited_org = st.data_editor(
        df_disp,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key="ed_org",
        column_config={
            "Kategoria": st.column_config.SelectboxColumn("Kategoria", options=all_cats, required=True),
            "Rola": st.column_config.TextColumn("Rola", required=True),
            "Informacje": st.column_config.TextColumn("Info", width="large"),
            "Koszt": st.column_config.NumberColumn("Koszt (zł)", format="%.0f zł", min_value=0, step=100),
            "Czy_Oplacone": st.column_config.CheckboxColumn("✅ Opłacone?"),
            "Zaliczka": st.column_config.NumberColumn("Zaliczka (zł)", format="%.0f zł", min_value=0, step=100),
            "Czy_Zaliczka_Oplacona": st.column_config.CheckboxColumn("✅ Zaliczka?")
        }
    )

    if st.button("💾 Zapisz (Budżet)", key="sav_org"):
        to_save = edited_org.copy()
        to_save = to_save[to_save["Rola"].str.strip() != ""]
        to_save = to_save.fillna("")
        
        # Konwersja bool -> "Tak"/"Nie" do arkusza
        df_arkusz = to_save.copy()
        df_arkusz["Czy_Oplacone"] = df_arkusz["Czy_Oplacone"].apply(lambda x: "Tak" if x else "Nie")
        df_arkusz["Czy_Zaliczka_Oplacona"] = df_arkusz["Czy_Zaliczka_Oplacona"].apply(lambda x: "Tak" if x else "Nie")
        
        aktualizuj_caly_arkusz(worksheet_obsluga, df_arkusz)
        
        # Aktualizacja session_state (bool)
        to_save["Czy_Oplacone"] = to_save["Czy_Oplacone"].apply(lambda x: x == True)
        to_save["Czy_Zaliczka_Oplacona"] = to_save["Czy_Zaliczka_Oplacona"].apply(lambda x: x == True)
        to_save["Koszt"] = pd.to_numeric(to_save["Koszt"], errors='coerce').fillna(0.0)
        to_save["Zaliczka"] = pd.to_numeric(to_save["Zaliczka"], errors='coerce').fillna(0.0)
        st.session_state["df_obsluga"] = to_save
        
        st.success("Zapisano!")
        st.rerun()

    # --- PODSUMOWANIE FINANSOWE ---
    if not df_obsluga.empty:
        calc = df_obsluga.copy()
        calc["Koszt"] = pd.to_numeric(calc["Koszt"], errors='coerce').fillna(0.0)
        calc["Zaliczka"] = pd.to_numeric(calc["Zaliczka"], errors='coerce').fillna(0.0)
        total = calc["Koszt"].sum()
        paid = 0.0
        for i, r in calc.iterrows():
            if r["Czy_Oplacone"]:
                paid += r["Koszt"]
            elif r["Czy_Zaliczka_Oplacona"]:
                paid += r["Zaliczka"]
        to_pay = total - paid

        st.write("---")
        card_style = "background-color: #262730; border: 1px solid #444; padding: 15px; border-radius: 10px; box-shadow: 2px 2px 10px rgba(0,0,0,0.5); text-align: left; margin-bottom: 10px;"
        c1, c2, c3 = st.columns(3)
        c1.markdown(f'<div style="{card_style}"><div style="color: #F5F5DC; font-size: 14px; margin-bottom: 5px;">Łącznie</div><div style="color: #4CAF50; font-size: 30px; font-weight: 700;">{total:,.0f} zł</div></div>', unsafe_allow_html=True)
        c2.markdown(f'<div style="{card_style}"><div style="color: #F5F5DC; font-size: 14px; margin-bottom: 5px;">Zapłacono</div><div style="color: #4CAF50; font-size: 30px; font-weight: 700;">{paid:,.0f} zł</div></div>', unsafe_allow_html=True)
        c3.markdown(f'<div style="{card_style}"><div style="color: #F5F5DC; font-size: 14px; margin-bottom: 5px;">Do zapłaty</div><div style="color: #ff4b4b; font-size: 30px; font-weight: 700;">{to_pay:,.0f} zł</div><div style="color: #ff4b4b; font-size: 14px;">▼ -{to_pay:,.0f}</div></div>', unsafe_allow_html=True)

        st.write("---")
        st.subheader("📊 Struktura Wydatków")
        grp = calc.groupby("Kategoria")["Koszt"].sum().reset_index().sort_values("Koszt", ascending=False)
        grp = grp[grp["Koszt"] > 0]
        if not grp.empty:
            st.write("**Ile wydajemy na co? (w zł)**")
            chart = alt.Chart(grp).mark_bar().encode(
                x=alt.X('Koszt', title='Kwota (zł)'),
                y=alt.Y('Kategoria', sort='-x', title='Kategoria'),
                color=alt.Color('Kategoria', legend=None),
                tooltip=['Kategoria', alt.Tooltip('Koszt', format=',.0f')]
            ).properties(height=300).interactive()
            st.altair_chart(chart, use_container_width=True)

            st.write("---")
            st.write("**Udział procentowy**")
            fig, ax = plt.subplots(figsize=(6, 6))
            fig.patch.set_alpha(0)
            ax.patch.set_alpha(0)
            wedges, texts, autotexts = ax.pie(
                grp["Koszt"],
                labels=grp["Kategoria"],
                autopct='%1.1f%%',
                startangle=90,
                textprops={'color': "white", 'fontsize': 10}
            )
            plt.setp(autotexts, size=10, weight="bold", color="white")
            plt.setp(texts, size=10, color="white")
            ax.axis('equal')
            c_center = st.columns([1,2,1])
            with c_center[1]:
                st.pyplot(fig, use_container_width=True)
                    # --- WYKRES KOŁOWY DLA RÓL (z tooltipami) ---
        st.write("---")
        st.write("**Wydatki według roli**")
        
        # Grupowanie po rolach
        grp_role = calc.groupby("Rola")["Koszt"].sum().reset_index().sort_values("Koszt", ascending=False)
        grp_role = grp_role[grp_role["Koszt"] > 0]
        
        if not grp_role.empty:
            # Interaktywny wykres kołowy Altair
            chart_pie_role = alt.Chart(grp_role).mark_arc(innerRadius=50).encode(
                theta=alt.Theta(field="Koszt", type="quantitative"),
                color=alt.Color(field="Rola", type="nominal", legend=alt.Legend(title="Rola")),
                tooltip=[
                    alt.Tooltip("Rola:N", title="Rola"),
                    alt.Tooltip("Koszt:Q", title="Koszt", format=",.0f")
                ]
            ).properties(
                width=400,
                height=400
            ).interactive()
            
            st.altair_chart(chart_pie_role, use_container_width=True)
        else:
            st.info("Brak danych do wyświetlenia wykresu dla ról.")
        else:
            st.info("Dodaj koszty, aby zobaczyć wykresy.")

# ==========================
# ZAKŁADKA 3: LISTA ZADAŃ
# ==========================
with tab3:
    st.header("✅ Co trzeba zrobić?")

    if "df_zadania" not in st.session_state:
        st.session_state["df_zadania"] = load_zadania()
    df_zadania = st.session_state["df_zadania"]

    def dodaj_zadanie():
        tresc = st.session_state.get("todo_tresc", "")
        termin = st.session_state.get("todo_data", date.today())
        if tresc:
            termin_str = termin.strftime("%Y-%m-%d")
            nowy_wiersz = [tresc, termin_str, False]
            df = st.session_state["df_zadania"].copy()
            nowy = dict(zip(KOLUMNY_ZADANIA, nowy_wiersz))
            df = pd.concat([df, pd.DataFrame([nowy])], ignore_index=True)
            st.session_state["df_zadania"] = df

            w_arkusz = nowy_wiersz.copy()
            w_arkusz[2] = "Tak" if w_arkusz[2] else "Nie"
            zapisz_nowy_wiersz(worksheet_zadania, w_arkusz)

            st.toast(f"📅 Dodano zadanie: {tresc}")
            st.session_state["todo_tresc"] = ""
        else:
            st.warning("Wpisz treść zadania!")

    with st.expander("➕ Dodaj nowe zadanie", expanded=False):
        c1, c2 = st.columns([2, 1])
        with c1:
            st.text_input("Co trzeba zrobić?", key="todo_tresc", placeholder="np. Kupić winietki")
        with c2:
            st.date_input("Termin wykonania", value=date.today(), key="todo_data")
        st.button("Dodaj do listy", on_click=dodaj_zadanie, key="btn_zadania")

    st.write("---")
    st.subheader(f"Lista Zadań ({len(df_zadania)})")

    df_todo_display = df_zadania.copy()
    df_todo_display["Zadanie"] = df_todo_display["Zadanie"].astype(str).replace("nan", "")
    df_todo_display["Termin"] = pd.to_datetime(df_todo_display["Termin"], errors='coerce').dt.date

    col_sort1, col_sort2 = st.columns([1, 3])
    with col_sort1:
        st.write("**Filtruj / Sortuj:**")
    with col_sort2:
        tryb_todo = st.radio(
            "Sortowanie Zadań",
            options=["📅 Najpilniejsze (Data)", "❌ Do zrobienia", "✅ Zrobione", "🔤 Nazwa (A-Z)"],
            label_visibility="collapsed",
            horizontal=True,
            key="sort_todo"
        )

    if tryb_todo == "📅 Najpilniejsze (Data)":
        df_todo_display = df_todo_display.sort_values(by="Termin", ascending=True)
    elif tryb_todo == "❌ Do zrobienia":
        df_todo_display = df_todo_display.sort_values(by="Czy_Zrobione", ascending=True)
    elif tryb_todo == "✅ Zrobione":
        df_todo_display = df_todo_display.sort_values(by="Czy_Zrobione", ascending=False)
    elif tryb_todo == "🔤 Nazwa (A-Z)":
        df_todo_display = df_todo_display.sort_values(by="Zadanie", ascending=True)

    edytowane_zadania = st.data_editor(
        df_todo_display,
        num_rows="dynamic",
        column_config={
            "Zadanie": st.column_config.TextColumn("Treść zadania", required=True, width="large"),
            "Termin": st.column_config.DateColumn("Termin", format="DD.MM.YYYY", step=1),
            "Czy_Zrobione": st.column_config.CheckboxColumn("Zrobione?", width="small")
        },
        use_container_width=True,
        hide_index=True,
        key="editor_zadania"
    )

    if st.button("💾 Zapisz zmiany", key="save_zadania"):
        df_to_save_todo = edytowane_zadania.copy()
        df_to_save_todo = df_to_save_todo[df_to_save_todo["Zadanie"].str.strip() != ""]
        df_to_save_todo["Termin"] = pd.to_datetime(df_to_save_todo["Termin"]).dt.strftime("%Y-%m-%d")
        df_arkusz = df_to_save_todo.copy()
        df_arkusz["Czy_Zrobione"] = df_arkusz["Czy_Zrobione"].apply(lambda x: "Tak" if x else "Nie")
        df_arkusz = df_arkusz.fillna("")
        aktualizuj_caly_arkusz(worksheet_zadania, df_arkusz)

        df_to_save_todo["Czy_Zrobione"] = df_to_save_todo["Czy_Zrobione"].apply(lambda x: x == True)
        st.session_state["df_zadania"] = df_to_save_todo
        st.success("Zaktualizowano listę zadań!")
        st.rerun()

    if not df_zadania.empty:
        total = len(df_zadania)
        zrobione = len(df_zadania[df_zadania["Czy_Zrobione"] == True])
        procent = int((zrobione / total) * 100) if total > 0 else 0
        st.write("---")
        st.progress(procent, text=f"Postęp prac: {zrobione}/{total} zadań ({procent}%)")
        if procent == 100:
            st.balloons()

# ==========================
# ZAKŁADKA 4: STOŁY
# ==========================
with tab4:
    st.header("🍽️ Rozsadzanie Gości przy Stołach")

    if "df_stoly" not in st.session_state:
        st.session_state["df_stoly"] = load_stoly()
    df_stoly = st.session_state["df_stoly"]

    col_left, col_right = st.columns([1, 2])

    with col_left:
        st.subheader("➕ Dodaj Stół")
        with st.form("dodaj_stol_form"):
            nr_stolu = st.text_input("Numer/Nazwa Stołu", placeholder="np. Stół 1 lub Wiejski")
            ksztalt = st.selectbox("Kształt", ["Okrągły", "Prostokątny"])
            miejsca = st.number_input("Liczba Miejsc", min_value=1, max_value=24, value=8)
            submitted = st.form_submit_button("Dodaj Stół")

            if submitted and nr_stolu:
                pusta_lista = ";".join(["" for _ in range(miejsca)])
                nowy_wiersz = [nr_stolu, ksztalt, miejsca, pusta_lista]
                df = st.session_state["df_stoly"].copy()
                nowy = dict(zip(KOLUMNY_STOLY, nowy_wiersz))
                df = pd.concat([df, pd.DataFrame([nowy])], ignore_index=True)
                st.session_state["df_stoly"] = df

                zapisz_nowy_wiersz(worksheet_stoly, nowy_wiersz)
                st.toast(f"Dodano stół: {nr_stolu}")

        st.write("---")
        st.subheader("📋 Lista Stołów")
        if not df_stoly.empty:
            list_of_tables = df_stoly["Numer"].tolist()
            wybrany_stol_id = st.radio("Wybierz stół do edycji:", list_of_tables)
        else:
            wybrany_stol_id = None
            st.info("Brak stołów. Dodaj pierwszy!")

    with col_right:
        if wybrany_stol_id:
            st.subheader(f"Edycja: {wybrany_stol_id}")

            row = df_stoly[df_stoly["Numer"] == wybrany_stol_id].iloc[0]
            max_miejsc = int(row["Liczba_Miejsc"])
            ksztalt_stolu = row["Ksztalt"]

            obecni_goscie_str = str(row["Goscie_Lista"])
            if ";" in obecni_goscie_str:
                lista_gosci = obecni_goscie_str.split(";")
            else:
                lista_gosci = [""] * max_miejsc

            if len(lista_gosci) < max_miejsc:
                lista_gosci += [""] * (max_miejsc - len(lista_gosci))
            lista_gosci = lista_gosci[:max_miejsc]

            with st.expander("📝 Przypisz gości do miejsc", expanded=True):
                nowa_lista_gosci = []
                c_a, c_b = st.columns(2)
                for i in range(max_miejsc):
                    col_to_use = c_a if i % 2 == 0 else c_b
                    with col_to_use:
                        val = st.text_input(f"Miejsce {i+1}", value=lista_gosci[i], key=f"seat_{wybrany_stol_id}_{i}")
                        nowa_lista_gosci.append(val)

                if st.button("💾 Zapisz układ stołu"):
                    zapis_string = ";".join(nowa_lista_gosci)
                    idx = int(df_stoly[df_stoly["Numer"] == wybrany_stol_id].index[0] + 2)
                    worksheet_stoly.update_cell(idx, 4, zapis_string)
                    st.cache_data.clear()
                    df = st.session_state["df_stoly"].copy()
                    mask = df["Numer"] == wybrany_stol_id
                    df.loc[mask, "Goscie_Lista"] = zapis_string
                    st.session_state["df_stoly"] = df
                    st.success("Zapisano!")
                    st.rerun()

            # Wizualizacja (skrócona dla przejrzystości)
            st.write("---")
            st.write(f"**Podgląd: {ksztalt_stolu} ({max_miejsc} os.)**")
            fig, ax = plt.subplots(figsize=(20, 16))
            fig.patch.set_alpha(0)
            ax.patch.set_alpha(0)
            ax.set_aspect('equal')
            ax.axis('off')
            table_color = '#9D5B03'
            seat_color = '#1B4D3E'
            text_color = 'white'
            edge_color = '#7B3F00'
            if ksztalt_stolu == "Okrągły":
                R_STOL = 1.1; R_KRZESLO_SRODEK = 1.4; R_TEKST = 1.65
                circle = plt.Circle((0, 0), R_STOL, color=table_color, ec=edge_color, lw=4); ax.add_artist(circle)
                ax.text(0, 0, wybrany_stol_id, ha='center', va='center', fontsize=24, fontweight='bold', color='white')
                for i in range(max_miejsc):
                    angle = 2 * np.pi * i / max_miejsc
                    cx = R_KRZESLO_SRODEK * np.cos(angle); cy = R_KRZESLO_SRODEK * np.sin(angle)
                    seat = plt.Circle((cx, cy), 0.21, color=seat_color, alpha=1.0); ax.add_artist(seat)
                    guest_name = nowa_lista_gosci[i]
                    tx = R_TEKST * np.cos(angle); ty = R_TEKST * np.sin(angle)
                    rot_deg = np.degrees(angle)
                    if 90 < rot_deg < 270: rot_deg += 180; ha = 'right'
                    else: ha = 'left'
                    if guest_name:
                        ax.text(tx, ty, guest_name, ha=ha, va='center', rotation=rot_deg, rotation_mode='anchor', fontsize=16, color=text_color, fontweight='bold')
                    else:
                        ax.text(cx, cy, str(i+1), ha='center', va='center', fontsize=16, color='white')
                ax.set_xlim(-2.2, 2.2); ax.set_ylim(-2.2, 2.2)
            else:
                W_STOL = 2.0; H_STOL = 4.0
                rect = plt.Rectangle((-W_STOL/2, -H_STOL/2), W_STOL, H_STOL, color=table_color, ec=edge_color, lw=4); ax.add_artist(rect)
                ax.text(0, 0, wybrany_stol_id, ha='center', va='center', rotation=90, fontsize=24, fontweight='bold', color='white')
                side_count = (max_miejsc + 1) // 2
                DIST_X = 1.3
                for i in range(max_miejsc):
                    guest_name = nowa_lista_gosci[i]
                    if i < side_count:
                        x_pos = -DIST_X; y_pos = np.linspace(-H_STOL/2 + 0.4, H_STOL/2 - 0.4, side_count)[i]; ha = 'right'; text_offset_x = -0.25
                    else:
                        x_pos = DIST_X; y_pos = np.linspace(-H_STOL/2 + 0.4, H_STOL/2 - 0.4, max_miejsc - side_count)[i - side_count]; ha = 'left'; text_offset_x = 0.25
                    seat = plt.Circle((x_pos, y_pos), 0.21, color=seat_color, alpha=1.0); ax.add_artist(seat)
                    if guest_name:
                        ax.text(x_pos + text_offset_x, y_pos, guest_name, ha=ha, va='center', fontsize=16, color=text_color, fontweight='bold')
                    else:
                        ax.text(x_pos, y_pos, str(i+1), ha='center', va='center', fontsize=16, color='white')
                ax.set_xlim(-2.8, 2.8); ax.set_ylim(-2.8, 2.8)
            st.pyplot(fig, use_container_width=True)

            st.write("---")
            if st.button("🗑️ Usuń ten stół"):
                idx = int(df_stoly[df_stoly["Numer"] == wybrany_stol_id].index[0] + 2)
                worksheet_stoly.delete_rows(idx)
                df = st.session_state["df_stoly"].copy()
                df = df[df["Numer"] != wybrany_stol_id]
                st.session_state["df_stoly"] = df
                st.cache_data.clear()
                st.warning("Usunięto stół!")
                st.rerun()
