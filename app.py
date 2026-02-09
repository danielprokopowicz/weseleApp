import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Menadżer Ślubny", page_icon="💍", layout="wide")

# --- POŁĄCZENIE Z GOOGLE SHEETS ---
# Funkcja z cache, żeby nie łączyć się przy każdym kliknięciu
@st.cache_resource
def polacz_z_arkuszem():
    # Pobieramy sekrety z ustawień Streamlit Cloud
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = dict(st.secrets["gcp_service_account"]) # Magia Streamlit Secrets
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    
    # Otwieramy arkusz po nazwie
    sheet = client.open("Wesele_Baza") 
    return sheet

try:
    sh = polacz_z_arkuszem()
    worksheet_goscie = sh.worksheet("Goscie")
    worksheet_obsluga = sh.worksheet("Obsluga")
except Exception as e:
    st.error(f"Błąd połączenia z Google Sheets! Sprawdź nazwę arkusza i uprawnienia. Błąd: {e}")
    st.stop()

# --- FUNKCJE POMOCNICZE ---
def pobierz_dane(worksheet):
    dane = worksheet.get_all_records()
    return pd.DataFrame(dane)

def zapisz_nowy_wiersz(worksheet, lista_wartosci):
    worksheet.append_row(lista_wartosci)

def aktualizuj_caly_arkusz(worksheet, df):
    # Czyścimy arkusz i wpisujemy nowe dane (to prosty sposób dla małych danych)
    worksheet.clear()
    worksheet.update([df.columns.values.tolist()] + df.values.tolist())

# --- TYTUŁ ---
st.title("💍 Menadżer Ślubny: Chmura Google")

tab1, tab2 = st.tabs(["👥 Lista Gości", "🎧 Obsługa i Koszty"])

# ==========================
# ZAKŁADKA 1: GOŚCIE
# ==========================
with tab1:
    st.header("Zarządzanie Gośćmi")
    
    # Pobieramy aktualne dane
    df_goscie = pobierz_dane(worksheet_goscie)
    
    # Jeśli arkusz jest pusty, dodajemy kolumny ręcznie do DataFrame
    if df_goscie.empty:
        df_goscie = pd.DataFrame(columns=["Imie_Nazwisko", "Osoba_Towarzyszaca", "RSVP"])

    # 1. Formularz
    with st.expander("➕ Dodaj nowego gościa"):
        col1, col2, col3 = st.columns(3)
        with col1:
            nowy_imie = st.text_input("Imię i Nazwisko")
        with col2:
            nowy_os_tow = st.checkbox("Osoba towarzysząca (+1)?", value=False)
        with col3:
            nowy_rsvp = st.checkbox("Potwierdzone (RSVP)?", value=False)
        
        if st.button("Dodaj do listy"):
            if nowy_imie:
                # Dodajemy bezpośrednio do Google Sheets (append)
                zapisz_nowy_wiersz(worksheet_goscie, [nowy_imie, "Tak" if nowy_os_tow else "Nie", "Tak" if nowy_rsvp else "Nie"])
                st.success(f"Dodano: {nowy_imie}")
                st.rerun()
            else:
                st.warning("Wpisz imię!")

    # 2. Tabela edytowalna
    st.subheader("📋 Lista Gości")
    
    # Konwersja dla lepszego wyświetlania (checkboxy zamiast tekstu Tak/Nie)
    df_display = df_goscie.copy()
    # Zamieniamy "Tak"/"Nie" na True/False dla edytora
    df_display["Osoba_Towarzyszaca"] = df_display["Osoba_Towarzyszaca"].apply(lambda x: True if x == "Tak" else False)
    df_display["RSVP"] = df_display["RSVP"].apply(lambda x: True if x == "Tak" else False)

    edytowane_goscie = st.data_editor(
        df_display, 
        num_rows="dynamic", 
        key="editor_goscie",
        use_container_width=True
    )

    # Przycisk zapisu zmian masowych
    if st.button("💾 Zapisz zmiany w tabeli (Goście)"):
        # Konwertujemy z powrotem na Tak/Nie przed wysłaniem do Google
        df_to_save = edytowane_goscie.copy()
        df_to_save["Osoba_Towarzyszaca"] = df_to_save["Osoba_Towarzyszaca"].apply(lambda x: "Tak" if x else "Nie")
        df_to_save["RSVP"] = df_to_save["RSVP"].apply(lambda x: "Tak" if x else "Nie")
        
        aktualizuj_caly_arkusz(worksheet_goscie, df_to_save)
        st.success("Zapisano zmiany w Google Sheets!")
        st.rerun()

# ==========================
# ZAKŁADKA 2: OBSŁUGA
# ==========================
with tab2:
    st.header("🎧 Organizacja")
    
    df_obsluga = pobierz_dane(worksheet_obsluga)
    if df_obsluga.empty:
        df_obsluga = pd.DataFrame(columns=["Rola", "Firma", "Koszt", "Zaliczka"])

    edytowana_obsluga = st.data_editor(
        df_obsluga,
        num_rows="dynamic",
        key="editor_obsluga",
        use_container_width=True
    )

    if st.button("💾 Zapisz zmiany (Obsługa)"):
        aktualizuj_caly_arkusz(worksheet_obsluga, edytowana_obsluga)
        st.success("Zapisano zmiany!")
        st.rerun()