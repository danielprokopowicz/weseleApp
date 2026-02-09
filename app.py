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
    st.header("Zarządzanie Gośćmi")

    # --- 0. Funkcja obsługująca kliknięcie (Callback) ---
    # To jest serce naprawy błędu. Ta funkcja wykona się w tle PRZED odświeżeniem ekranu.
    def obsluga_dodawania():
        # Pobieramy wartości bezpośrednio z "pamięci" formularza
        imie_glowne = st.session_state.get("input_imie", "")
        imie_partnera = st.session_state.get("input_partner", "")
        czy_rsvp = st.session_state.get("check_rsvp", False)
        czy_z_osoba = st.session_state.get("check_plusone", False)

        if imie_glowne:
            rsvp_text = "Tak" if czy_rsvp else "Nie"
            
            # 1. Dodajemy głównego gościa
            # Uwaga: używamy 'worksheet_goscie' który jest zdefiniowany wyżej w skrypcie
            zapisz_nowy_wiersz(worksheet_goscie, [imie_glowne, "", rsvp_text])
            st.toast(f"✅ Dodano: {imie_glowne}") # Wyświetli ładny dymek sukcesu

            # 2. Dodajemy osobę towarzyszącą (jeśli zaznaczono)
            if czy_z_osoba and imie_partnera:
                zapisz_nowy_wiersz(worksheet_goscie, [imie_partnera, f"(Osoba tow. dla: {imie_glowne})", rsvp_text])
            
            # 3. RESETOWANIE PÓL (To teraz zadziała bezpiecznie!)
            st.session_state["input_imie"] = ""
            st.session_state["input_partner"] = ""
            st.session_state["check_rsvp"] = False
            st.session_state["check_plusone"] = False
        else:
            st.warning("Musisz wpisać imię głównego gościa!")

    # Pobieranie danych z Google (żeby tabela była aktualna)
    try:
        df_goscie = pobierz_dane(worksheet_goscie)
    except Exception as e:
        st.error("Błąd danych.")
        st.stop()
    
    if df_goscie.empty:
        df_goscie = pd.DataFrame(columns=["Imie_Nazwisko", "Imie_Osoby_Tow", "RSVP"])

    # --- 1. Formularz Dodawania (Interfejs) ---
    with st.expander("➕ Dodaj nowego gościa", expanded=True):
        
        # Checkbox decydujący o układzie
        # Musimy użyć key, żeby funkcja callback mogła go zresetować
        czy_z_osoba = st.checkbox("Chcę dodać też osobę towarzyszącą (+1)", key="check_plusone")

        c1, c2 = st.columns(2)
        with c1:
            st.text_input("Imię i Nazwisko Gościa", key="input_imie")
        with c2:
            # Pole partnera pokazuje się tylko gdy checkbox jest zaznaczony
            if czy_z_osoba:
                st.text_input("Imię Osoby Towarzyszącej", key="input_partner")

        st.checkbox("Czy potwierdzili przybycie (RSVP)?", key="check_rsvp")
        
        # PRZYCISK: Zauważ, że nie ma tu 'if st.button'.
        # Jest parametr 'on_click', który wywołuje naszą funkcję naprawczą z góry.
        st.button("Dodaj do listy", on_click=obsluga_dodawania)

    # --- 2. Tabela ---
    st.write("---")
    st.subheader(f"📋 Lista Gości ({len(df_goscie)} pozycji)")

    df_display = df_goscie.copy()
    # Konwersja RSVP na checkbox (bezpieczna)
    df_display["RSVP"] = df_display["RSVP"].apply(lambda x: True if str(x).lower() == "tak" else False)

    edytowane_goscie = st.data_editor(
        df_display,
        num_rows="dynamic",
        column_config={
            "Imie_Nazwisko": st.column_config.TextColumn("Imię i Nazwisko"),
            "Imie_Osoby_Tow": st.column_config.TextColumn("Info (+1)", disabled=True),
            "RSVP": st.column_config.CheckboxColumn("RSVP")
        },
        use_container_width=True,
        key="editor_goscie"
    )

    if st.button("💾 Zapisz zmiany w tabeli (Goście)"):
        df_to_save = edytowane_goscie.copy()
        df_to_save["RSVP"] = df_to_save["RSVP"].apply(lambda x: "Tak" if x else "Nie")
        df_to_save = df_to_save.fillna("")
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
