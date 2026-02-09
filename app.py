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
    
    # Pobieranie danych
    try:
        df_goscie = pobierz_dane(worksheet_goscie)
    except Exception as e:
        st.error("Błąd pobierania danych. Upewnij się, że w Arkuszu Google wiersz 1 zawiera nagłówki: 'Imie_Nazwisko', 'Imie_Osoby_Tow', 'RSVP'.")
        st.stop()
    
    # Inicjalizacja pustej tabeli jeśli brak danych
    if df_goscie.empty:
        df_goscie = pd.DataFrame(columns=["Imie_Nazwisko", "Imie_Osoby_Tow", "RSVP"])

    # --- 1. Formularz Dodawania ---
    with st.expander("➕ Dodaj nowego gościa", expanded=True):
        col1, col2 = st.columns([1, 1])
        
        with col1:
            nowy_imie = st.text_input("Imię i Nazwisko Gościa")
            czy_rsvp = st.checkbox("Czy potwierdzili przybycie (RSVP)?")

        with col2:
            # Logika pokazywania pola dla osoby towarzyszącej
            czy_z_osoba = st.checkbox("Czy z osobą towarzyszącą?")
            
            imie_osoby_tow = ""
            if czy_z_osoba:
                imie_osoby_tow = st.text_input("Imię Osoby Towarzyszącej")
        
        btn_dodaj = st.button("Dodaj do listy")

        if btn_dodaj:
            if nowy_imie:
                # Formatowanie danych do zapisu
                rsvp_text = "Tak" if czy_rsvp else "Nie"
                # Jeśli nie zaznaczono os. tow, pole zostaje puste
                
                zapisz_nowy_wiersz(worksheet_goscie, [nowy_imie, imie_osoby_tow, rsvp_text])
                st.success(f"Dodano: {nowy_imie}")
                st.rerun()
            else:
                st.warning("Musisz wpisać imię głównego gościa!")

    # --- 2. Tabela Edytowalna ---
    st.write("---")
    st.subheader(f"📋 Lista Gości ({len(df_goscie)} pozycji)")

    # Przygotowanie danych do wyświetlenia
    # Streamlit lubi typ bool (True/False) dla checkboxów, więc konwertujemy kolumnę RSVP
    df_display = df_goscie.copy()
    
    # Zabezpieczenie na wypadek gdyby w arkuszu były dziwne dane
    df_display["RSVP"] = df_display["RSVP"].apply(lambda x: True if str(x).lower() == "tak" else False)

    # Konfiguracja edytora
    edytowane_goscie = st.data_editor(
        df_display,
        num_rows="dynamic",
        column_config={
            "Imie_Nazwisko": st.column_config.TextColumn("Główny Gość"),
            "Imie_Osoby_Tow": st.column_config.TextColumn("Osoba Towarzysząca (Imię)", help="Wpisz imię lub zostaw puste"),
            "RSVP": st.column_config.CheckboxColumn("Potwierdzone?", default=False)
        },
        use_container_width=True,
        key="editor_goscie"
    )

    # Przycisk zapisu zmian
    if st.button("💾 Zapisz zmiany w tabeli (Goście)"):
        # Konwersja z powrotem na format do Google Sheets
        df_to_save = edytowane_goscie.copy()
        df_to_save["RSVP"] = df_to_save["RSVP"].apply(lambda x: "Tak" if x else "Nie")
        # Upewniamy się, że puste pola to puste stringi, a nie NaN
        df_to_save = df_to_save.fillna("")
        
        aktualizuj_caly_arkusz(worksheet_goscie, df_to_save)
        st.success("Zapisano zmiany w Google Sheets!")
        st.rerun()

    # --- 3. Statystyki ---
    if not df_goscie.empty:
        # Liczymy ile osób łącznie (główni + towarzyszący, jeśli mają wpisane imię)
        liczba_glownych = len(df_goscie)
        # Zliczamy niepuste pola w kolumnie osób towarzyszących
        liczba_towarzyszacych = df_goscie[df_goscie["Imie_Osoby_Tow"] != ""].shape[0]
        
        st.info(f"Razem osób na liście: {liczba_glownych + liczba_towarzyszacych} (Goście: {liczba_glownych}, Towarzyszący: {liczba_towarzyszacych})")

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
