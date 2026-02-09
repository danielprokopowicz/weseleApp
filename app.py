import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Menadżer Ślubny", page_icon="💍", layout="wide")

# --- POŁĄCZENIE Z GOOGLE SHEETS ---
@st.cache_resource
def polacz_z_arkuszem():
    # Pobieramy sekrety
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    
    # Otwieramy arkusz
    try:
        sheet = client.open("Wesele_Baza")
        return sheet
    except Exception as e:
        st.error(f"Nie znaleziono arkusza 'Wesele_Baza'. Upewnij się, że nazwa jest poprawna i udostępniłeś go mailowi robota.")
        st.stop()

# Inicjalizacja połączenia
try:
    sh = polacz_z_arkuszem()
    worksheet_goscie = sh.worksheet("Goscie")
    worksheet_obsluga = sh.worksheet("Obsluga")
except Exception as e:
    st.error(f"Błąd arkusza: {e}. Sprawdź czy zakładki nazywają się 'Goscie' i 'Obsluga' oraz czy Wiersz 1 zawiera nagłówki bez pustych pól!")
    st.stop()

# --- FUNKCJE POMOCNICZE ---
def pobierz_dane(worksheet):
    # get_all_records wymaga, aby 1. wiersz był nagłówkami i nie miał pustych komórek w środku zakresu
    dane = worksheet.get_all_records()
    return pd.DataFrame(dane)

def zapisz_nowy_wiersz(worksheet, lista_wartosci):
    worksheet.append_row(lista_wartosci)

def aktualizuj_caly_arkusz(worksheet, df):
    worksheet.clear()
    # Zapisujemy nagłówki i dane
    worksheet.update([df.columns.values.tolist()] + df.values.tolist())

# --- UI APLIKACJI ---
st.title("💍 Menadżer Ślubny")

tab1, tab2 = st.tabs(["👥 Lista Gości", "🎧 Obsługa i Koszty"])

# ==========================
# ZAKŁADKA 1: GOŚCIE
# ==========================
with tab1:
    # --- CSS HACK: Ukrywanie paska dodawania (Plusa) ---
    st.markdown("""
        <style>
        /* Ukrywa ostatni wiersz w tabeli (ten szary z plusem) */
        [data-testid="stDataEditor"] table tbody tr:last-child {
            display: none;
        }
        /* Dla nowszych wersji Streamlit (Glide Data Grid) - to ukrywa przycisk "trail" */
        iframe[title="data_editor"] {
            clip-path: inset(0px 0px 35px 0px);
        }
        </style>
    """, unsafe_allow_html=True)
    st.header("Zarządzanie Gośćmi")

    # --- 0. Funkcja obsługująca kliknięcie DODAJ (Callback) ---
    def obsluga_dodawania():
        imie_glowne = st.session_state.get("input_imie", "")
        imie_partnera = st.session_state.get("input_partner", "")
        czy_rsvp = st.session_state.get("check_rsvp", False)
        czy_z_osoba = st.session_state.get("check_plusone", False)

        if imie_glowne:
            rsvp_text = "Tak" if czy_rsvp else "Nie"
            
            # 1. Główny gość
            zapisz_nowy_wiersz(worksheet_goscie, [imie_glowne, "", rsvp_text])
            st.toast(f"✅ Dodano: {imie_glowne}")

            # 2. Osoba towarzysząca
            if czy_z_osoba and imie_partnera:
                zapisz_nowy_wiersz(worksheet_goscie, [imie_partnera, f"(Osoba tow. dla: {imie_glowne})", rsvp_text])
            
            # 3. Reset
            st.session_state["input_imie"] = ""
            st.session_state["input_partner"] = ""
            st.session_state["check_rsvp"] = False
            st.session_state["check_plusone"] = False
        else:
            st.warning("Musisz wpisać imię głównego gościa!")

    # Pobieranie danych
    try:
        df_goscie = pobierz_dane(worksheet_goscie)
    except Exception as e:
        st.error("Błąd danych.")
        st.stop()
    
    if df_goscie.empty:
        df_goscie = pd.DataFrame(columns=["Imie_Nazwisko", "Imie_Osoby_Tow", "RSVP"])

    # --- 1. Formularz Dodawania ---
    with st.expander("➕ Dodaj nowego gościa", expanded=True):
        czy_z_osoba = st.checkbox("Chcę dodać też osobę towarzyszącą (+1)", key="check_plusone")

        c1, c2 = st.columns(2)
        with c1:
            st.text_input("Imię i Nazwisko Gościa", key="input_imie")
        with c2:
            if czy_z_osoba:
                st.text_input("Imię Osoby Towarzyszącej", key="input_partner")

        st.checkbox("Potwierdzenie Przybycia", key="check_rsvp")
        st.button("Dodaj do listy", on_click=obsluga_dodawania)

    # --- 2. Tabela Edycji i Usuwania ---
    st.write("---")
    st.subheader(f"📋 Lista Gości ({len(df_goscie)} pozycji)")
    st.caption("ℹ️ Aby usunąć: zaznacz wiersz po lewej stronie (kliknij w numer) i naciśnij ikonę kosza 🗑️ w prawym górnym rogu tabeli.")

    df_display = df_goscie.copy()
    
    # Konwersja RSVP na checkbox
    df_display["RSVP"] = df_display["RSVP"].apply(lambda x: True if str(x).lower() == "tak" else False)

    edytowane_goscie = st.data_editor(
        df_display,
        num_rows="dynamic", # To włącza pasek narzędzi z koszem!
        column_config={
            "Imie_Nazwisko": st.column_config.TextColumn("Imię i Nazwisko", required=True),
            "Imie_Osoby_Tow": st.column_config.TextColumn("Info (+1) / Powiązanie"),
            "RSVP": st.column_config.CheckboxColumn("Potwierdzenie Przybycia")
        },
        use_container_width=True,
        key="editor_goscie"
    )

    if st.button("💾 Zapisz zmiany (Edycja / Usuwanie)"):
        # 1. Bierzemy edytowaną tabelę
        df_to_save = edytowane_goscie.copy()
        
        # 2. ZABEZPIECZENIE: Usuwamy puste wiersze
        # Jeśli ktoś kliknął "+" w tabeli, ale nie wpisał imienia, to ten wiersz wyrzucamy.
        # Dzięki temu dodawanie działa tylko przez górny formularz.
        df_to_save = df_to_save[df_to_save["Imie_Nazwisko"].str.len() > 0]

        # 3. Konwersja RSVP
        df_to_save["RSVP"] = df_to_save["RSVP"].apply(lambda x: "Tak" if x else "Nie")
        df_to_save = df_to_save.fillna("")
        
        # 4. Wysyłamy do Google (nadpisujemy arkusz aktualnym stanem tabeli)
        aktualizuj_caly_arkusz(worksheet_goscie, df_to_save)
        
        st.success("Zapisano zmiany w Google Sheets!")
        st.rerun()

    if not df_goscie.empty:
        potwierdzone = df_goscie[df_goscie["RSVP"].astype(str) == "Tak"]
        st.info(f"Gości: {len(df_goscie)} | Potwierdziło: {len(potwierdzone)}")
        
# ==========================
# ZAKŁADKA 2: OBSŁUGA
# ==========================
with tab2:
    st.header("🎧 Organizacja")
    
    try:
        df_obsluga = pobierz_dane(worksheet_obsluga)
    except:
        df_obsluga = pd.DataFrame(columns=["Rola", "Firma", "Koszt", "Zaliczka"])

    if df_obsluga.empty:
        df_obsluga = pd.DataFrame(columns=["Rola", "Firma", "Koszt", "Zaliczka"])

    edytowana_obsluga = st.data_editor(
        df_obsluga,
        num_rows="dynamic",
        use_container_width=True,
        key="editor_obsluga"
    )

    if st.button("💾 Zapisz zmiany (Obsługa)"):
        aktualizuj_caly_arkusz(worksheet_obsluga, edytowana_obsluga)
        st.success("Zapisano zmiany!")
        st.rerun()
