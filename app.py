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

    # --- 0. Funkcja obsługująca kliknięcie DODAJ (Górny Formularz) ---
    def obsluga_dodawania():
        imie_glowne = st.session_state.get("input_imie", "")
        imie_partnera = st.session_state.get("input_partner", "")
        czy_rsvp = st.session_state.get("check_rsvp", False)
        czy_z_osoba = st.session_state.get("check_plusone", False)

        if imie_glowne:
            rsvp_text = "Tak" if czy_rsvp else "Nie"
            
            # Dodajemy do arkusza (to pozwoli od razu zobaczyć wynik po odświeżeniu)
            zapisz_nowy_wiersz(worksheet_goscie, [imie_glowne, "", rsvp_text])
            
            if czy_z_osoba and imie_partnera:
                zapisz_nowy_wiersz(worksheet_goscie, [imie_partnera, f"(Osoba tow. dla: {imie_glowne})", rsvp_text])
            
            st.toast(f"✅ Dodano: {imie_glowne}")
            
            # Reset formularza
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
        st.error("Błąd danych z Google Sheets.")
        st.stop()
    
    # Zabezpieczenie: Jeśli arkusz jest pusty, tworzymy pustą ramkę danych
    if df_goscie.empty:
        df_goscie = pd.DataFrame(columns=["Imie_Nazwisko", "Imie_Osoby_Tow", "RSVP"])

    # --- 1. Formularz Dodawania (Szybki) ---
    with st.expander("➕ Szybkie dodawanie (Formularz)", expanded=False):
        czy_z_osoba = st.checkbox("Chcę dodać też osobę towarzyszącą (+1)", key="check_plusone")
        c1, c2 = st.columns(2)
        with c1:
            st.text_input("Imię i Nazwisko Gościa", key="input_imie")
        with c2:
            if czy_z_osoba:
                st.text_input("Imię Osoby Towarzyszącej", key="input_partner")
        st.checkbox("Potwierdzenie Przybycia", key="check_rsvp")
        st.button("Dodaj do listy", on_click=obsluga_dodawania)

    # --- 2. Główna Tabela (Pełna edycja) ---
    st.write("---")
    st.subheader(f"📋 Lista Gości ({len(df_goscie)} pozycji)")
    st.info("💡 Kliknij nagłówek kolumny, aby posortować. Użyj + na dole tabeli, aby dodać wiersz ręcznie.")

    # PRZYGOTOWANIE DANYCH (Kluczowe dla sortowania!)
    df_display = df_goscie.copy()
    
    # 1. Wymuszamy, że kolumny tekstowe są na pewno tekstem (str), a puste to pusty napis
    df_display["Imie_Nazwisko"] = df_display["Imie_Nazwisko"].astype(str).replace("nan", "")
    df_display["Imie_Osoby_Tow"] = df_display["Imie_Osoby_Tow"].astype(str).replace("nan", "")

    # 2. Konwersja RSVP na Boolean (True/False) dla checkboxów
    # Używamy mapowania, które jest bezpieczniejsze dla sortowania
    df_display["RSVP"] = df_display["RSVP"].apply(lambda x: True if str(x).lower() in ["tak", "true", "1"] else False)

    # EDYTOR
    edytowane_goscie = st.data_editor(
        df_display,
        num_rows="dynamic", # Włącza: Dodawanie (+), Usuwanie (Kosz)
        column_config={
            "Imie_Nazwisko": st.column_config.TextColumn("Imię i Nazwisko", required=True),
            "Imie_Osoby_Tow": st.column_config.TextColumn("Info (+1) / Powiązanie"),
            "RSVP": st.column_config.CheckboxColumn("Potwierdzenie Przybycia")
        },
        use_container_width=True,
        # Ukrywamy indeks (0,1,2), żeby było ładniej, usuwanie nadal działa po zaznaczeniu wiersza
        hide_index=False, 
        key="editor_goscie"
    )

    # ZAPISYWANIE
    if st.button("💾 Zapisz wszystkie zmiany (Tabela)"):
        df_to_save = edytowane_goscie.copy()
        
        # 1. Usuwamy całkowicie puste wiersze (jeśli ktoś kliknął + i zostawił puste)
        df_to_save = df_to_save[df_to_save["Imie_Nazwisko"].str.strip() != ""]
        
        # 2. Konwersja z powrotem na Tak/Nie
        df_to_save["RSVP"] = df_to_save["RSVP"].apply(lambda x: "Tak" if x else "Nie")
        
        # 3. Zastępowanie NaN (Brak danych) pustymi stringami, żeby Google Sheets nie zgłupiał
        df_to_save = df_to_save.fillna("")
        
        # 4. Wysyłka
        aktualizuj_caly_arkusz(worksheet_goscie, df_to_save)
        
        st.success("Zapisano zmiany w Google Sheets!")
        st.rerun()

    # Statystyki na dole
    if not df_goscie.empty:
        potwierdzone = df_goscie[df_goscie["RSVP"].astype(str) == "Tak"]
        st.info(f"Gości na liście: {len(df_goscie)} | Potwierdziło przybycie: {len(potwierdzone)}")
        
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
