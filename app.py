import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import date

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
    try:
        worksheet_zadania = sh.worksheet("Zadania")
    except:
        worksheet_zadania = None
        st.warning("⚠️ Brakuje zakładki 'Zadania' w Arkuszu Google! Stwórz ją, aby lista zadań działała.")
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

tab1, tab2, tab3 = st.tabs(["👥 Lista Gości", "🎧 Organizacja", "✅ Lista Zadań"])

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
        czy_zaproszenie = st.session_state.get("check_invite", False)

        if imie_glowne:
            rsvp_text = "Tak" if czy_rsvp else "Nie"
            invite_text = "Tak" if czy_zaproszenie else "Nie"
            
            zapisz_nowy_wiersz(worksheet_goscie, [imie_glowne, "", rsvp_text, invite_text])
            
            if czy_z_osoba and imie_partnera:
                zapisz_nowy_wiersz(worksheet_goscie, [imie_partnera, f"(Osoba tow. dla: {imie_glowne})", rsvp_text, invite_text])
            
            st.toast(f"✅ Dodano: {imie_glowne}")
            
            st.session_state["input_imie"] = ""
            st.session_state["input_partner"] = ""
            st.session_state["check_rsvp"] = False
            st.session_state["check_plusone"] = False
            st.session_state["check_invite"] = False
        else:
            st.warning("Musisz wpisać imię głównego gościa!")

    # Pobieranie danych
    try:
        df_goscie = pobierz_dane(worksheet_goscie)
    except Exception as e:
        st.error(f"Błąd w zakładce GOŚCIE: {e}. Sprawdź czy dodałeś kolumnę 'Zaproszenie_Wyslane' w D1.")
        st.stop()
    
    if df_goscie.empty:
        df_goscie = pd.DataFrame(columns=["Imie_Nazwisko", "Imie_Osoby_Tow", "RSVP", "Zaproszenie_Wyslane"])

    if "Zaproszenie_Wyslane" not in df_goscie.columns:
        df_goscie["Zaproszenie_Wyslane"] = "Nie"

    # --- 1. Formularz Dodawania ---
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

    # --- 2. Główna Tabela ---
    st.write("---")
    st.subheader(f"📋 Lista Gości ({len(df_goscie)} pozycji)")

    # --- PRZYGOTOWANIE DANYCH ---
    df_display = df_goscie.copy()
    
    df_display["Imie_Nazwisko"] = df_display["Imie_Nazwisko"].astype(str).replace("nan", "")
    df_display["Imie_Osoby_Tow"] = df_display["Imie_Osoby_Tow"].astype(str).replace("nan", "")

    def parsuj_bool(wartosc):
        return str(wartosc).lower() in ["tak", "true", "1", "yes"]
    
    df_display["RSVP"] = df_display["RSVP"].apply(parsuj_bool)
    df_display["Zaproszenie_Wyslane"] = df_display["Zaproszenie_Wyslane"].apply(parsuj_bool)

    # --- RĘCZNE SORTOWANIE ---
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

    # EDYTOR DANYCH
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

    # ZAPISYWANIE - TUTAJ BYŁ BŁĄD, DODAŁEM KEY="save_goscie"
    if st.button("💾 Zapisz zmiany", key="save_goscie"):
        df_to_save = edytowane_goscie.copy()
        
        df_to_save = df_to_save[df_to_save["Imie_Nazwisko"].str.strip() != ""]
        
        df_to_save["RSVP"] = df_to_save["RSVP"].apply(lambda x: "Tak" if x else "Nie")
        df_to_save["Zaproszenie_Wyslane"] = df_to_save["Zaproszenie_Wyslane"].apply(lambda x: "Tak" if x else "Nie")
        
        df_to_save = df_to_save.fillna("")
        
        aktualizuj_caly_arkusz(worksheet_goscie, df_to_save)
        st.success("Zapisano zmiany!")
        st.rerun()

    # Statystyki
    if not df_goscie.empty:
        potwierdzone = df_goscie[df_goscie["RSVP"].astype(str) == "Tak"]
        zaproszone = df_goscie[df_goscie["Zaproszenie_Wyslane"].astype(str) == "Tak"]
        
        k1, k2, k3 = st.columns(3)
        k1.metric("Liczba gości", f"{len(df_goscie)}")
        k2.metric("Wysłane zaproszenia", f"{len(zaproszone)}")
        k3.metric("Potwierdzone Przybycia", f"{len(potwierdzone)}")

# ==========================
# ZAKŁADKA 2: ORGANIZACJA I BUDŻET
# ==========================
with tab2:
    st.header("🎧 Organizacja i Budżet")

    def dodaj_usluge():
        rola = st.session_state.get("org_rola", "")
        info = st.session_state.get("org_info", "")
        koszt = st.session_state.get("org_koszt", 0.0)
        czy_oplacone = st.session_state.get("org_oplacone", False)
        
        zaliczka_kwota = st.session_state.get("org_zaliczka_kwota", 0.0)
        czy_zaliczka_oplacona = st.session_state.get("org_zaliczka_oplacona", False)

        if rola:
            txt_oplacone = "Tak" if czy_oplacone else "Nie"
            txt_zaliczka_opl = "Tak" if czy_zaliczka_oplacona else "Nie"

            zapisz_nowy_wiersz(worksheet_obsluga, [rola, info, koszt, txt_oplacone, zaliczka_kwota, txt_zaliczka_opl])
            st.toast(f"💰 Dodano usługę: {rola}")

            st.session_state["org_rola"] = ""
            st.session_state["org_info"] = ""
            st.session_state["org_koszt"] = 0.0
            st.session_state["org_oplacone"] = False
            st.session_state["org_zaliczka_kwota"] = 0.0
            st.session_state["org_zaliczka_oplacona"] = False
        else:
            st.warning("Musisz wpisać nazwę Roli (np. DJ, Fotograf)!")

    try:
        df_obsluga = pobierz_dane(worksheet_obsluga)
    except Exception as e:
        st.error("Błąd danych. Sprawdź nagłówki w zakładce Obsluga.")
        st.stop()

    if df_obsluga.empty:
        df_obsluga = pd.DataFrame(columns=["Rola", "Informacje", "Koszt", "Czy_Oplacone", "Zaliczka", "Czy_Zaliczka_Oplacona"])

    with st.expander("➕ Dodaj nową usługę / koszt", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            st.text_input("Rola (np. DJ, Sala)", key="org_rola")
            st.number_input("Całkowity Koszt (zł)", min_value=0.0, step=100.0, key="org_koszt")
            st.checkbox("Czy całość już opłacona?", key="org_oplacone")
        with c2:
            st.text_input("Informacje dodatkowe (Kontakt)", key="org_info")
            st.number_input("Wymagana Zaliczka (0 jeśli brak)", min_value=0.0, step=100.0, key="org_zaliczka_kwota")
            st.checkbox("Czy zaliczka opłacona?", key="org_zaliczka_oplacona")
        
        st.button("Dodaj do budżetu", on_click=dodaj_usluge)

    st.write("---")
    st.subheader(f"💸 Lista Wydatków ({len(df_obsluga)} pozycji)")

    df_org_display = df_obsluga.copy()

    df_org_display["Koszt"] = pd.to_numeric(df_org_display["Koszt"], errors='coerce').fillna(0.0)
    df_org_display["Zaliczka"] = pd.to_numeric(df_org_display["Zaliczka"], errors='coerce').fillna(0.0)
    df_org_display["Rola"] = df_org_display["Rola"].astype(str).replace("nan", "")
    df_org_display["Informacje"] = df_org_display["Informacje"].astype(str).replace("nan", "")

    def napraw_booleana(x):
        return str(x).lower().strip() in ["tak", "true", "1", "yes"]

    df_org_display["Czy_Oplacone"] = df_org_display["Czy_Oplacone"].apply(napraw_booleana)
    df_org_display["Czy_Zaliczka_Oplacona"] = df_org_display["Czy_Zaliczka_Oplacona"].apply(napraw_booleana)

    col_sort1, col_sort2 = st.columns([1, 3])
    with col_sort1:
        st.write("**Sortuj wg:**")
    with col_sort2:
        tryb_finanse = st.radio(
            "Sortowanie Finansów",
            options=["Domyślnie", "💰 Najdroższe na górze", "❌ Nieopłacone na górze", "✅ Opłacone na górze", "🔤 Rola (A-Z)"],
            label_visibility="collapsed",
            horizontal=True,
            key="sort_finanse"
        )

    if tryb_finanse == "💰 Najdroższe na górze":
        df_org_display = df_org_display.sort_values(by="Koszt", ascending=False)
    elif tryb_finanse == "❌ Nieopłacone na górze":
        df_org_display = df_org_display.sort_values(by="Czy_Oplacone", ascending=True)
    elif tryb_finanse == "✅ Opłacone na górze":
        df_org_display = df_org_display.sort_values(by="Czy_Oplacone", ascending=False)
    elif tryb_finanse == "🔤 Rola (A-Z)":
        df_org_display = df_org_display.sort_values(by="Rola", ascending=True)

    edytowana_obsluga = st.data_editor(
        df_org_display,
        num_rows="dynamic",
        column_config={
            "Rola": st.column_config.TextColumn("Rola / Usługa", required=True),
            "Informacje": st.column_config.TextColumn("Kontakt / Info", width="medium"),
            "Koszt": st.column_config.NumberColumn("Koszt (Całość)", format="%d zł", step=100),
            "Czy_Oplacone": st.column_config.CheckboxColumn("✅ Opłacone?"),
            "Zaliczka": st.column_config.NumberColumn("Zaliczka", format="%d zł", step=100),
            "Czy_Zaliczka_Oplacona": st.column_config.CheckboxColumn("✅ Zaliczka wpłacona?")
        },
        use_container_width=True,
        hide_index=True,
        key="editor_obsluga"
    )

    # ZAPISYWANIE - TUTAJ BYŁ BŁĄD, DODAŁEM KEY="save_obsluga"
    if st.button("💾 Zapisz zmiany", key="save_obsluga"):
        df_to_save_org = edytowana_obsluga.copy()
        
        df_to_save_org = df_to_save_org[df_to_save_org["Rola"].str.strip() != ""]
        
        df_to_save_org["Czy_Oplacone"] = df_to_save_org["Czy_Oplacone"].apply(lambda x: "Tak" if x else "Nie")
        df_to_save_org["Czy_Zaliczka_Oplacona"] = df_to_save_org["Czy_Zaliczka_Oplacona"].apply(lambda x: "Tak" if x else "Nie")
        
        df_to_save_org = df_to_save_org.fillna("")

        aktualizuj_caly_arkusz(worksheet_obsluga, df_to_save_org)
        st.success("Zapisano budżet!")
        st.rerun()

    if not df_org_display.empty:
        st.write("---")
        total_koszt = df_org_display["Koszt"].sum()
        
        wydano = 0.0
        for index, row in df_org_display.iterrows():
            if row["Czy_Oplacone"]:
                wydano += row["Koszt"]
            elif row["Czy_Zaliczka_Oplacona"]:
                wydano += row["Zaliczka"]
        
        pozostalo = total_koszt - wydano

        k1, k2, k3 = st.columns(3)
        k1.metric("Łączny koszt", f"{total_koszt:,.0f} zł".replace(",", " "))
        k2.metric("Już zapłacono", f"{wydano:,.0f} zł".replace(",", " "))
        k3.metric("Pozostało do zapłaty", f"{pozostalo:,.0f} zł".replace(",", " "), delta=f"-{pozostalo} zł", delta_color="inverse")

# ==========================
# ZAKŁADKA 3: LISTA ZADAŃ (TO-DO)
# ==========================
with tab3:
    st.header("✅ Co trzeba zrobić?")

    def dodaj_zadanie():
        tresc = st.session_state.get("todo_tresc", "")
        termin = st.session_state.get("todo_data", date.today())
        
        if tresc:
            termin_str = termin.strftime("%Y-%m-%d")
            
            zapisz_nowy_wiersz(worksheet_zadania, [tresc, termin_str, "Nie"])
            st.toast(f"📅 Dodano zadanie: {tresc}")

            st.session_state["todo_tresc"] = ""
        else:
            st.warning("Wpisz treść zadania!")

    try:
        df_zadania = pobierz_dane(worksheet_zadania)
    except Exception as e:
        st.error("Błąd danych. Sprawdź nagłówki w zakładce Zadania.")
        st.stop()

    if df_zadania.empty:
        df_zadania = pd.DataFrame(columns=["Zadanie", "Termin", "Czy_Zrobione"])

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

    def napraw_booleana(x):
        return str(x).lower().strip() in ["tak", "true", "1", "yes"]
    df_todo_display["Czy_Zrobione"] = df_todo_display["Czy_Zrobione"].apply(napraw_booleana)

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

    # ZAPISYWANIE - TUTAJ DODAŁEM KEY="save_zadania"
    if st.button("💾 Zapisz zmiany", key="save_zadania"):
        df_to_save_todo = edytowane_zadania.copy()
        
        df_to_save_todo = df_to_save_todo[df_to_save_todo["Zadanie"].str.strip() != ""]
        
        df_to_save_todo["Termin"] = pd.to_datetime(df_to_save_todo["Termin"]).dt.strftime("%Y-%m-%d")

        df_to_save_todo["Czy_Zrobione"] = df_to_save_todo["Czy_Zrobione"].apply(lambda x: "Tak" if x else "Nie")
        
        df_to_save_todo = df_to_save_todo.fillna("")

        aktualizuj_caly_arkusz(worksheet_zadania, df_to_save_todo)
        st.success("Zaktualizowano listę zadań!")
        st.rerun()

    if not df_zadania.empty:
        total = len(df_zadania)
        zrobione = len(df_zadania[df_zadania["Czy_Zrobione"].apply(napraw_booleana)])
        procent = int((zrobione / total) * 100) if total > 0 else 0
        
        st.write("---")
        st.progress(procent, text=f"Postęp prac: {zrobione}/{total} zadań ({procent}%)")
        if procent == 100:
            st.balloons()
