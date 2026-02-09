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

    # --- 0. Logika Resetowania Formularza ---
    # Musimy zainicjować "pamięć" formularza, jeśli jeszcze nie istnieje
    if "input_imie" not in st.session_state:
        st.session_state["input_imie"] = ""
    if "input_partner" not in st.session_state:
        st.session_state["input_partner"] = ""
    if "check_rsvp" not in st.session_state:
        st.session_state["check_rsvp"] = False
    if "check_plusone" not in st.session_state:
        st.session_state["check_plusone"] = False

    # Pobieranie danych z Google Sheets
    try:
        df_goscie = pobierz_dane(worksheet_goscie)
    except Exception as e:
        st.error("Błąd pobierania danych. Sprawdź nagłówki w Google Sheets.")
        st.stop()
    
    if df_goscie.empty:
        df_goscie = pd.DataFrame(columns=["Imie_Nazwisko", "Imie_Osoby_Tow", "RSVP"])

    # --- 1. Formularz Dodawania (Nowy Wygląd) ---
    with st.expander("➕ Dodaj nowego gościa", expanded=True):
        
        # Checkbox na samej górze, żeby nie psuł układu pól tekstowych
        czy_z_osoba = st.checkbox("Chcę dodać też osobę towarzyszącą (+1)", key="check_plusone")

        # Dwie kolumny na pola tekstowe - będą idealnie równe
        c1, c2 = st.columns(2)
        with c1:
            # key="input_imie" pozwala nam potem wyczyścić to pole
            imie_glowne = st.text_input("Imię i Nazwisko Gościa", key="input_imie")
        with c2:
            if czy_z_osoba:
                imie_partnera = st.text_input("Imię Osoby Towarzyszącej", key="input_partner")
            else:
                imie_partnera = ""

        # Checkbox RSVP na dole
        czy_rsvp = st.checkbox("Czy potwierdzili przybycie (RSVP)?", key="check_rsvp")
        
        btn_dodaj = st.button("Dodaj do listy")

        if btn_dodaj:
            if imie_glowne:
                rsvp_text = "Tak" if czy_rsvp else "Nie"
                
                # KROK A: Dodajemy głównego gościa
                # Wpisujemy pusty string w kolumnie "Imie_Osoby_Tow", bo teraz to osobny wiersz
                zapisz_nowy_wiersz(worksheet_goscie, [imie_glowne, "", rsvp_text])
                komunikat = f"Dodano: {imie_glowne}"

                # KROK B: Jeśli jest osoba towarzysząca, dodajemy ją jako OSOBNY wiersz
                if czy_z_osoba and imie_partnera:
                    zapisz_nowy_wiersz(worksheet_goscie, [imie_partnera, f"(Osoba tow. dla: {imie_glowne})", rsvp_text])
                    komunikat += f" oraz {imie_partnera}"

                st.success(komunikat)

                # KROK C: Resetowanie pól (Czyszczenie formularza)
                st.session_state["input_imie"] = ""
                st.session_state["input_partner"] = ""
                st.session_state["check_rsvp"] = False
                st.session_state["check_plusone"] = False
                
                # Odświeżamy stronę, żeby zobaczyć zmiany i wyczyszczone pola
                st.rerun()
            else:
                st.warning("Musisz wpisać imię głównego gościa!")

    # --- 2. Tabela ---
    st.write("---")
    st.subheader(f"📋 Lista Gości ({len(df_goscie)} pozycji)")

    # Wyświetlanie tabeli (bez zmian logicznych, tylko estetyka)
    df_display = df_goscie.copy()
    # Konwersja RSVP na checkbox dla wygody edycji
    df_display["RSVP"] = df_display["RSVP"].apply(lambda x: True if str(x).lower() == "tak" else False)

    edytowane_goscie = st.data_editor(
        df_display,
        num_rows="dynamic",
        column_config={
            "Imie_Nazwisko": st.column_config.TextColumn("Imię i Nazwisko"),
            "Imie_Osoby_Tow": st.column_config.TextColumn("Notatki / Powiązanie", help="Tutaj pojawi się info kogo to osoba towarzysząca", disabled=True),
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

    # Statystyki na dole
    if not df_goscie.empty:
        potwierdzone = df_goscie[df_goscie["RSVP"].astype(str) == "Tak"]
        st.info(f"Liczba gości na liście: {len(df_goscie)} | Potwierdziło: {len(potwierdzone)}")
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
