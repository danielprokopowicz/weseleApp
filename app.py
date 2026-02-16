import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import date
import matplotlib.pyplot as plt
import altair as alt
import numpy as np
from gspread.exceptions import WorksheetNotFound
from fpdf import FPDF         
import io                     

# --- STYLIZACJA CSS ---
def local_css():
    st.markdown("""
    <style>
        html, body, [class*="css"] { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; }
        .block-container { padding-top: 1rem !important; padding-bottom: 2rem !important; }
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
        @media only screen and (max-width: 600px) {
            .block-container {
                padding-left: 0.5rem !important;
                padding-right: 0.5rem !important;
            }
            h1 { font-size: 1.8rem; }
            h2 { font-size: 1.4rem; }
            [data-testid="stMetric"] {
                padding: 10px;
            }
            [data-testid="stMetricValue"] {
                font-size: 24px !important;
            }
            button[data-baseweb="tab"] {
                font-size: 14px !important;
                padding: 4px 8px !important;
            }
            .stDataEditor {
                font-size: 12px;
            }
        }
        .stApp header [data-testid="stDecoration"] { display: none; }
        .stApp header [data-testid="stStatusWidget"] { display: none; }
        .stApp header [data-testid="stToolbar"] { display: none; }
    </style>
    """, unsafe_allow_html=True)

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Menadżer Ślubny", page_icon="💍", layout="wide", initial_sidebar_state="expanded")
local_css()

# --- WCZYTANIE DATY Z URL (jeśli istnieje) ---
from datetime import datetime

def pobierz_date_z_url():
    """Zwraca datę z query_params lub domyślną."""
    domyslna = date(2027, 7, 13)
    params = st.query_params
    if "data_slubu" in params:
        try:
            # params["data_slubu"] to string (nie lista)
            return datetime.strptime(params["data_slubu"], "%Y-%m-%d").date()
        except:
            return domyslna
    return domyslna

# Inicjalizacja daty w session_state (dla bieżącej sesji)
if "data_slubu" not in st.session_state:
    st.session_state["data_slubu"] = pobierz_date_z_url()

# --- SIDEBAR Z DATĄ ŚLUBU ---
with st.sidebar:
    st.header("⚙️ Ustawienia")
    nowa_data = st.date_input("Wybierz datę ślubu", value=st.session_state["data_slubu"])
    if nowa_data != st.session_state["data_slubu"]:
        st.session_state["data_slubu"] = nowa_data
        # Zapis do URL (trwały)
        st.query_params["data_slubu"] = nowa_data.strftime("%Y-%m-%d")
        st.rerun()
    st.caption(f"Obecna data: {st.session_state['data_slubu'].strftime('%d.%m.%Y')}")

# --- LICZNIK (wyświetlany pod tytułem) ---
st.title("💍 Menadżer Ślubny")
dzisiaj = date.today()
data_slubu = st.session_state["data_slubu"]
if dzisiaj <= data_slubu:
    pozostalo = (data_slubu - dzisiaj).days
    st.info(f"💍 **Do ślubu pozostało {pozostalo} dni!**")
else:
    st.success("🎉 Wesele już było! Czas na miesiąc miodowy!")
    
# --- STAŁE KOLUMN ---
KOLUMNY_GOSCIE = ["Imie_Nazwisko", "Imie_Osoby_Tow", "RSVP", "Zaproszenie_Wyslane", "Dieta"]
KOLUMNY_OBSLUGA  = ["Kategoria", "Rola", "Informacje", "Koszt", "Czy_Oplacone", "Zaliczka", "Czy_Zaliczka_Oplacona"]
KOLUMNY_ZADANIA  = ["Zadanie", "Termin", "Czy_Zrobione"]
KOLUMNY_STOLY    = ["Numer", "Ksztalt", "Liczba_Miejsc", "Goscie_Lista"]
KOLUMNY_HARMONOGRAM = ["Godzina", "Czynność", "Uwagi"]

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
    try:
        arkusze["Harmonogram"] = sh.worksheet("Harmonogram")
    except WorksheetNotFound:
        arkusze["Harmonogram"] = None
        st.warning("⚠️ Brak zakładki 'Harmonogram' – harmonogram dnia nie będzie dostępny.")
    return arkusze

arkusze = pobierz_arkusze()
worksheet_goscie  = arkusze["Goscie"]
worksheet_obsluga = arkusze["Obsluga"]
worksheet_zadania = arkusze["Zadania"]
worksheet_stoly   = arkusze["Stoly"]
worksheet_harmonogram = arkusze.get("Harmonogram")

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
    if "Dieta" not in df.columns:
        df["Dieta"] = ""
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

def load_harmonogram():
    if worksheet_harmonogram is None:
        return pd.DataFrame(columns=KOLUMNY_HARMONOGRAM)
    df = pobierz_dane(worksheet_harmonogram)
    if 'ID' in df.columns:
        df = df.drop(columns=['ID'])
    if df.empty:
        df = pd.DataFrame(columns=KOLUMNY_HARMONOGRAM)
    for col in KOLUMNY_HARMONOGRAM:
        if col not in df.columns:
            df[col] = ""
    df = df.fillna("")
    df["Godzina"] = df["Godzina"].astype(str)
    return df

# --- FUNKCJA GENERUJĄCA PDF ---
def generuj_pdf(goscie_df, stoly_df, harmonogram_df):
    import os
    import unicodedata
    from io import BytesIO

    def usun_polskie_znaki(tekst):
        return ''.join(
            c for c in unicodedata.normalize('NFD', tekst)
            if unicodedata.category(c) != 'Mn'
        )

    pdf = FPDF()
    
    czcionka_ok = os.path.exists("fonts/DejaVuSans.ttf")
    if czcionka_ok:
        pdf.add_font("DejaVu", "", "fonts/DejaVuSans.ttf")
        pdf.set_font("DejaVu", size=12)
        font_family = "DejaVu"
        clean_text = lambda x: x
    else:
        pdf.set_font("helvetica", size=12)
        font_family = "helvetica"
        clean_text = usun_polskie_znaki
        st.warning("Używam domyślnej czcionki – polskie znaki mogą być niepoprawne.")

    pdf.add_page()

    # Tytuł
    pdf.set_font(font_family, size=16)
    pdf.cell(200, 10, txt=clean_text("Podsumowanie wesela"), ln=1, align='C')
    pdf.ln(10)

    # --- Lista gości ---
    pdf.set_font(font_family, size=14)
    pdf.cell(200, 10, txt=clean_text("Lista gości"), ln=1)
    pdf.set_font(font_family, size=10)
    if not goscie_df.empty:
        for _, row in goscie_df.iterrows():
            pdf.cell(200, 8, txt=clean_text(row['Imie_Nazwisko']), ln=1)
    else:
        pdf.cell(200, 8, txt=clean_text("Brak gości"), ln=1)
    pdf.ln(5)

    # --- Podsumowanie diet (tylko potwierdzeni goście) ---
    if not goscie_df.empty and 'Dieta' in goscie_df.columns:
        potwierdzeni = goscie_df[goscie_df['RSVP'] == True]
        if not potwierdzeni.empty:
            dieta_counts = potwierdzeni['Dieta'].value_counts().reset_index()
            dieta_counts.columns = ['Opcja', 'Liczba']
            # Filtrujemy puste diety (jeśli ktoś nie wybrał)
            dieta_counts = dieta_counts[dieta_counts['Opcja'] != ""]
            
            if not dieta_counts.empty:
                pdf.set_font(font_family, size=14)
                pdf.cell(200, 10, txt=clean_text("Podsumowanie diet"), ln=1)
                pdf.set_font(font_family, size=10)
                for _, row in dieta_counts.iterrows():
                    linia = f"{row['Opcja']}: {row['Liczba']}"
                    pdf.cell(200, 8, txt=clean_text(linia), ln=1)
                pdf.ln(5)
        else:
            pdf.set_font(font_family, size=12)
            pdf.cell(200, 8, txt=clean_text("Brak potwierdzonych gości – brak danych o dietach"), ln=1)
            pdf.ln(5)
    else:
        pdf.set_font(font_family, size=12)
        pdf.cell(200, 8, txt=clean_text("Brak danych o dietach"), ln=1)
        pdf.ln(5)

    # --- Rozsadzenie przy stołach ---
    pdf.set_font(font_family, size=14)
    pdf.cell(200, 10, txt=clean_text("Rozsadzenie przy stołach"), ln=1)
    pdf.set_font(font_family, size=10)
    if not stoly_df.empty:
        for _, row in stoly_df.iterrows():
            linia = f"Stół {row['Numer']} ({row['Ksztalt']}, {row['Liczba_Miejsc']} miejsc):"
            pdf.cell(200, 8, txt=clean_text(linia), ln=1)
            goscie_przy_stole = row['Goscie_Lista'].split(';') if row['Goscie_Lista'] else []
            goscie_przy_stole = [g for g in goscie_przy_stole if g.strip()]
            if goscie_przy_stole:
                for gosc in goscie_przy_stole:
                    pdf.cell(200, 6, txt=clean_text(f"   - {gosc}"), ln=1)
            else:
                pdf.cell(200, 6, txt=clean_text("   (brak gości)"), ln=1)
    else:
        pdf.cell(200, 8, txt=clean_text("Brak danych o stołach"), ln=1)
    pdf.ln(5)

    # --- Harmonogram dnia ---
    pdf.set_font(font_family, size=14)
    pdf.cell(200, 10, txt=clean_text("Harmonogram dnia"), ln=1)
    pdf.set_font(font_family, size=10)
    if not harmonogram_df.empty:
        harm_sorted = harmonogram_df.copy()
        try:
            harm_sorted['czas'] = pd.to_datetime(harm_sorted['Godzina'], format='%H:%M', errors='coerce')
            harm_sorted = harm_sorted.sort_values('czas').drop(columns=['czas'])
        except:
            harm_sorted = harm_sorted.sort_values('Godzina')
        for _, row in harm_sorted.iterrows():
            txt = f"{row['Godzina']} - {row['Czynność']}"
            if row['Uwagi']:
                txt += f" ({row['Uwagi']})"
            pdf.cell(200, 8, txt=clean_text(txt), ln=1)
    else:
        pdf.cell(200, 8, txt=clean_text("Brak harmonogramu"), ln=1)

    # Generowanie PDF
    pdf_bytes = pdf.output()
    if isinstance(pdf_bytes, str):
        pdf_bytes = pdf_bytes.encode('utf-8')
    return BytesIO(pdf_bytes)
    
# --- UI APLIKACJI ---
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["👥 Lista Gości", "🎧 Organizacja", "✅ Lista Zadań", "🍽️ Rozplanowanie Stołów", "⏰ Harmonogram Dnia", "🍽️ Diety"])

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
            nowe_wiersze.append([imie_glowne, "", czy_rsvp, czy_zaproszenie, ""])  # pusta dieta
            if czy_z_osoba and imie_partnera:
                nowe_wiersze.append([imie_partnera, f"(Osoba tow. dla: {imie_glowne})", czy_rsvp, czy_zaproszenie, ""])

            df = st.session_state["df_goscie"].copy()
            for w in nowe_wiersze:
                nowy = dict(zip(KOLUMNY_GOSCIE, w))
                df = pd.concat([df, pd.DataFrame([nowy])], ignore_index=True)
            st.session_state["df_goscie"] = df

            for w in nowe_wiersze:
                w_arkusz = w.copy()
                w_arkusz[2] = "Tak" if w_arkusz[2] else "Nie"
                w_arkusz[3] = "Tak" if w_arkusz[3] else "Nie"
                zapisz_nowy_wiersz(worksheet_goscie, w_arkusz)

            st.toast(f"✅ Dodano: {imie_glowne}")
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
            "RSVP": st.column_config.CheckboxColumn("✅ Potwierdzone Przybycie", default=False),
            "Dieta": st.column_config.SelectboxColumn("Dieta", options=["", "Mięsna", "Wegetariańska", "Wegańska", "Bezglutenowa", "Inna"], required=False)
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

    # --- Generator PDF ---
    st.write("---")
    st.subheader("📄 Eksport do PDF")
    if st.button("Generuj PDF"):
        goscie_df = st.session_state.get("df_goscie", pd.DataFrame())
        stoly_df = st.session_state.get("df_stoly", pd.DataFrame())
        harmonogram_df = st.session_state.get("df_harmonogram", pd.DataFrame())
        
        pdf_buffer = generuj_pdf(goscie_df, stoly_df, harmonogram_df)
        
        st.download_button(
            label="📥 Pobierz PDF",
            data=pdf_buffer,
            file_name="podsumowanie_wesela.pdf",
            mime="application/pdf"
        )

# ==========================
# ZAKŁADKA 2: ORGANIZACJA
# ==========================
with tab2:
    st.header("🎧 Organizacja i Budżet")
    
    if "df_obsluga" not in st.session_state:
        st.session_state["df_obsluga"] = load_obsluga()
    df_obsluga = st.session_state["df_obsluga"]

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
            df = st.session_state["df_obsluga"].copy()
            nowy = dict(zip(KOLUMNY_OBSLUGA, nowy_wiersz))
            df = pd.concat([df, pd.DataFrame([nowy])], ignore_index=True)
            st.session_state["df_obsluga"] = df

            w_arkusz = nowy_wiersz.copy()
            w_arkusz[4] = "Tak" if w_arkusz[4] else "Nie"
            w_arkusz[6] = "Tak" if w_arkusz[6] else "Nie"
            zapisz_nowy_wiersz(worksheet_obsluga, w_arkusz)

            st.toast(f"💰 Dodano: {r}")
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

    fil = st.multiselect("🔍 Filtruj:", all_cats)
    df_disp = df_obsluga.copy()
    if fil:
        df_disp = df_disp[df_disp["Kategoria"].isin(fil)]

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
        
        df_arkusz = to_save.copy()
        df_arkusz["Czy_Oplacone"] = df_arkusz["Czy_Oplacone"].apply(lambda x: "Tak" if x else "Nie")
        df_arkusz["Czy_Zaliczka_Oplacona"] = df_arkusz["Czy_Zaliczka_Oplacona"].apply(lambda x: "Tak" if x else "Nie")
        
        aktualizuj_caly_arkusz(worksheet_obsluga, df_arkusz)
        
        to_save["Czy_Oplacone"] = to_save["Czy_Oplacone"].apply(lambda x: x == True)
        to_save["Czy_Zaliczka_Oplacona"] = to_save["Czy_Zaliczka_Oplacona"].apply(lambda x: x == True)
        to_save["Koszt"] = pd.to_numeric(to_save["Koszt"], errors='coerce').fillna(0.0)
        to_save["Zaliczka"] = pd.to_numeric(to_save["Zaliczka"], errors='coerce').fillna(0.0)
        st.session_state["df_obsluga"] = to_save
        
        st.success("Zapisano!")
        st.rerun()

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
        
        grp_cat = calc.groupby("Kategoria")["Koszt"].sum().reset_index().sort_values("Koszt", ascending=False)
        grp_cat = grp_cat[grp_cat["Koszt"] > 0]
        if not grp_cat.empty:
            st.write("**Ile wydajemy na poszczególne kategorie?**")
            chart_bar = alt.Chart(grp_cat).mark_bar().encode(
                x=alt.X('Koszt', title='Kwota (zł)'),
                y=alt.Y('Kategoria', sort='-x', title='Kategoria'),
                color=alt.Color('Kategoria', legend=None),
                tooltip=['Kategoria', alt.Tooltip('Koszt', format=',.0f')]
            ).properties(height=300).interactive()
            st.altair_chart(chart_bar, use_container_width=True)

        st.write("---")
        st.write("**Wydatki według roli**")
        grp_role = calc.groupby("Rola")["Koszt"].sum().reset_index().sort_values("Koszt", ascending=False)
        grp_role = grp_role[grp_role["Koszt"] > 0]
        if not grp_role.empty:
            chart_pie_role = alt.Chart(grp_role).mark_arc(innerRadius=50).encode(
                theta=alt.Theta(field="Koszt", type="quantitative"),
                color=alt.Color(field="Rola", type="nominal", legend=alt.Legend(title="Rola")),
                tooltip=[
                    alt.Tooltip("Rola:N", title="Rola"),
                    alt.Tooltip("Koszt:Q", title="Koszt", format=",.0f")
                ]
            ).properties(width=400, height=400).interactive()
            st.altair_chart(chart_pie_role, use_container_width=True)
        else:
            st.info("Brak danych do wyświetlenia wykresu dla ról.")

        if not grp_cat.empty:
            st.write("---")
            st.write("**Udział procentowy kategorii**")
            chart_pie_cat = alt.Chart(grp_cat).mark_arc(innerRadius=50).encode(
                theta=alt.Theta(field="Koszt", type="quantitative"),
                color=alt.Color(field="Kategoria", type="nominal", legend=alt.Legend(title="Kategoria")),
                tooltip=[
                    alt.Tooltip("Kategoria:N", title="Kategoria"),
                    alt.Tooltip("Koszt:Q", title="Koszt", format=",.0f")
                ]
            ).properties(width=400, height=400).interactive()
            st.altair_chart(chart_pie_cat, use_container_width=True)
    else:
        st.info("Dodaj koszty, aby zobaczyć podsumowanie i wykresy.")

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

# ==========================
# ZAKŁADKA 5: HARMONOGRAM DNIA
# ==========================
with tab5:
    st.header("⏰ Harmonogram Dnia Ślubu (minuta po minucie)")

    if "df_harmonogram" not in st.session_state:
        st.session_state["df_harmonogram"] = load_harmonogram()
    df_harm = st.session_state["df_harmonogram"]

    def dodaj_wydarzenie():
        godz = st.session_state.get("harm_godz", "")
        czyn = st.session_state.get("harm_czyn", "")
        uwagi = st.session_state.get("harm_uwagi", "")
        if godz and czyn:
            nowy = [godz, czyn, uwagi]
            df = st.session_state["df_harmonogram"].copy()
            nowy_dict = dict(zip(KOLUMNY_HARMONOGRAM, nowy))
            df = pd.concat([df, pd.DataFrame([nowy_dict])], ignore_index=True)
            st.session_state["df_harmonogram"] = df

            w_arkusz = nowy.copy()
            zapisz_nowy_wiersz(worksheet_harmonogram, w_arkusz)

            st.toast(f"✅ Dodano: {godz} – {czyn}")
            st.session_state["harm_godz"] = ""
            st.session_state["harm_czyn"] = ""
            st.session_state["harm_uwagi"] = ""
        else:
            st.warning("Wpisz godzinę i czynność!")

    with st.expander("➕ Dodaj nowe wydarzenie", expanded=False):
        c1, c2, c3 = st.columns([1,2,2])
        with c1:
            st.text_input("Godzina (np. 16:30)", key="harm_godz", placeholder="HH:MM")
        with c2:
            st.text_input("Czynność", key="harm_czyn", placeholder="np. Pierwszy taniec")
        with c3:
            st.text_input("Uwagi (opcjonalnie)", key="harm_uwagi", placeholder="dla kogo, gdzie...")
        st.button("Dodaj do harmonogramu", on_click=dodaj_wydarzenie, key="btn_harm")

    st.write("---")
    st.subheader(f"📅 Harmonogram ({len(df_harm)} pozycji)")

    df_disp_harm = df_harm.copy()
    # Usuń ewentualną kolumnę ID
    if 'ID' in df_disp_harm.columns:
        df_disp_harm = df_disp_harm.drop(columns=['ID'])

    # Sortowanie po godzinie
    try:
        df_disp_harm["czas_sort"] = pd.to_datetime(df_disp_harm["Godzina"], format="%H:%M", errors='coerce')
        df_disp_harm = df_disp_harm.sort_values("czas_sort").drop(columns=["czas_sort"])
    except:
        df_disp_harm = df_disp_harm.sort_values("Godzina")

    # Konwersja wszystkich kolumn na string – zapobiega błędom typów w data_editor
    df_disp_harm = df_disp_harm.fillna("").astype(str)

    edited_harm = st.data_editor(
        df_disp_harm,
        num_rows="dynamic",
        column_config={
            "Godzina": st.column_config.TextColumn("Godzina", required=True, width="small"),
            "Czynność": st.column_config.TextColumn("Czynność", required=True, width="large"),
            "Uwagi": st.column_config.TextColumn("Uwagi", width="large")
        },
        use_container_width=True,
        hide_index=True,
        key="editor_harm"
    )

    if st.button("💾 Zapisz harmonogram", key="save_harm"):
        to_save = edited_harm.copy()
        to_save = to_save[to_save["Godzina"].str.strip() != ""]
        to_save = to_save[to_save["Czynność"].str.strip() != ""]
        to_save = to_save.fillna("")
        if 'ID' in to_save.columns:
            to_save = to_save.drop(columns=['ID'])
        aktualizuj_caly_arkusz(worksheet_harmonogram, to_save)
        st.session_state["df_harmonogram"] = to_save
        st.success("Zapisano harmonogram!")
        st.rerun()

# ==========================
# ZAKŁADKA 6: MENU I DIETY
# ==========================
with tab6:
    st.header("🍽️ Zarządzanie dietami")

    if "df_goscie" not in st.session_state:
        st.session_state["df_goscie"] = load_goscie()
    df_goscie = st.session_state["df_goscie"]

    # Filtruj tylko gości z potwierdzonym przybyciem (opcjonalnie)
    potwierdzeni = df_goscie[df_goscie["RSVP"] == True].copy()
    if potwierdzeni.empty:
        st.info("Brak gości z potwierdzonym przybyciem.")
    else:
        st.write(f"**Liczba potwierdzonych gości:** {len(potwierdzeni)}")

        # Edytor diet
        edited_diety = st.data_editor(
            potwierdzeni[["Imie_Nazwisko", "Dieta"]],
            num_rows="fixed",
            use_container_width=True,
            hide_index=True,
            key="editor_diety",
            column_config={
                "Imie_Nazwisko": st.column_config.TextColumn("Gość", disabled=True),
                "Dieta": st.column_config.SelectboxColumn(
                    "Opcja diety",
                    options=["", "Mięsna", "Wegetariańska", "Wegańska", "Bezglutenowa", "Inna"],
                    required=False
                )
            }
        )

        # Przycisk zapisu zmian do arkusza
        if st.button("💾 Zapisz diety", key="save_diety"):
            # Zaktualizuj oryginalny DataFrame
            df_all = st.session_state["df_goscie"].copy()
            for index, row in edited_diety.iterrows():
                mask = df_all["Imie_Nazwisko"] == row["Imie_Nazwisko"]
                df_all.loc[mask, "Dieta"] = row["Dieta"]
            st.session_state["df_goscie"] = df_all

            # Zapisz do arkusza (całość)
            df_arkusz = df_all.copy()
            df_arkusz["RSVP"] = df_arkusz["RSVP"].apply(lambda x: "Tak" if x else "Nie")
            df_arkusz["Zaproszenie_Wyslane"] = df_arkusz["Zaproszenie_Wyslane"].apply(lambda x: "Tak" if x else "Nie")
            df_arkusz = df_arkusz.fillna("")
            aktualizuj_caly_arkusz(worksheet_goscie, df_arkusz)

            st.success("Diety zapisane!")
            st.rerun()

        # Podsumowanie dla cateringu
        st.write("---")
        st.subheader("📊 Podsumowanie diet (potwierdzeni goście)")

        dieta_counts = edited_diety["Dieta"].value_counts().reset_index()
        dieta_counts.columns = ["Opcja", "Liczba"]

        # Wyświetl w ładnej tabelce
        col1, col2 = st.columns([2, 1])
        with col1:
            st.dataframe(dieta_counts, hide_index=True, use_container_width=True)
        with col2:
            # Prosty wykres kołowy Altair
            if not dieta_counts.empty:
                chart = alt.Chart(dieta_counts).mark_arc(innerRadius=30).encode(
                    theta=alt.Theta(field="Liczba", type="quantitative"),
                    color=alt.Color(field="Opcja", type="nominal"),
                    tooltip=["Opcja", "Liczba"]
                ).properties(width=250, height=250).interactive()
                st.altair_chart(chart, use_container_width=True)

        # Eksport do pliku dla kuchni
        st.write("---")
        if st.button("📄 Pobierz listę diet (CSV)"):
            csv = dieta_counts.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Pobierz CSV",
                data=csv,
                file_name="podsumowanie_diet.csv",
                mime="text/csv"
            )
