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

    # --- 0. Funkcja obsługująca kliknięcie DODAJ ---
    def obsluga_dodawania():
        imie_glowne = st.session_state.get("input_imie", "")
        imie_partnera = st.session_state.get("input_partner", "")
        czy_rsvp = st.session_state.get("check_rsvp", False)
        czy_z_osoba = st.session_state.get("check_plusone", False)

        if imie_glowne:
            rsvp_text = "Tak" if czy_rsvp else "Nie"
            
            zapisz_nowy_wiersz(worksheet_goscie, [imie_glowne, "", rsvp_text])
            
            if czy_z_osoba and imie_partnera:
                zapisz_nowy_wiersz(worksheet_goscie, [imie_partnera, f"(Osoba tow. dla: {imie_glowne})", rsvp_text])
            
            st.toast(f"✅ Dodano: {imie_glowne}")
            
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
    
    if df_goscie.empty:
        df_goscie = pd.DataFrame(columns=["Imie_Nazwisko", "Imie_Osoby_Tow", "RSVP"])

    # --- 1. Formularz Dodawania ---
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

    # --- 2. Główna Tabela ---
    st.write("---")
    st.subheader(f"📋 Lista Gości ({len(df_goscie)} pozycji)")
    
    # Usunąłem st.info o plusie, zgodnie z życzeniem.

    # --- PRZYGOTOWANIE DANYCH DO SORTOWANIA ---
    df_display = df_goscie.copy()
    
    # 1. Konwersja tekstów: Zamieniamy wszystkie "nulle" i liczby na tekst (string)
    # To jest kluczowe dla sortowania alfabetycznego!
    df_display["Imie_Nazwisko"] = df_display["Imie_Nazwisko"].astype(str).replace("nan", "")
    df_display["Imie_Osoby_Tow"] = df_display["Imie_Osoby_Tow"].astype(str).replace("nan", "")

    # 2. Konwersja RSVP na logiczny (True/False)
    # Dzięki temu sortowanie dzieli na: Zaznaczone vs Niezaznaczone
    def parsuj_rsvp(wartosc):
        s = str(wartosc).lower().strip()
        return s in ["tak", "true", "1", "yes"]

    df_display["RSVP"] = df_display["RSVP"].apply(parsuj_rsvp)

    # EDYTOR DANYCH
    edytowane_goscie = st.data_editor(
        df_display,
        num_rows="dynamic", # Plus i Kosz są aktywne
        column_config={
            "Imie_Nazwisko": st.column_config.TextColumn(
                "Imię i Nazwisko", 
                required=True,
                width="medium"
            ),
            "Imie_Osoby_Tow": st.column_config.TextColumn(
                "Info (+1) / Powiązanie",
                width="large"
            ),
            "RSVP": st.column_config.CheckboxColumn(
                "Potwierdzenie Przybycia",
                default=False
            )
        },
        use_container_width=True,
        hide_index=True, # Ukryłem indeks (0,1,2), żeby było czyściej. Usuwanie nadal działa (zaznacz wiersz).
        key="editor_goscie"
    )

    # ZAPISYWANIE
    if st.button("💾 Zapisz wszystkie zmiany (Tabela)"):
        df_to_save = edytowane_goscie.copy()
        
        # Usuwamy puste wiersze (zabezpieczenie przed pustym plusem)
        df_to_save = df_to_save[df_to_save["Imie_Nazwisko"].str.strip() != ""]
        
        # Konwersja RSVP z powrotem na Tak/Nie
        df_to_save["RSVP"] = df_to_save["RSVP"].apply(lambda x: "Tak" if x else "Nie")
        
        # Zastępowanie braków danych
        df_to_save = df_to_save.fillna("")
        
        aktualizuj_caly_arkusz(worksheet_goscie, df_to_save)
        st.success("Zapisano zmiany!")
        st.rerun()

    # Statystyki
    if not df_goscie.empty:
        potwierdzone = df_goscie[df_goscie["RSVP"].astype(str) == "Tak"]
        st.metric("Liczba gości", f"{len(df_goscie)}", delta=f"{len(potwierdzone)} potwierdzonych")
        
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
