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
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    try:
        sheet = client.open("Wesele_Baza")
        return sheet
    except Exception as e:
        st.error(f"Nie znaleziono arkusza 'Wesele_Baza'.")
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
except Exception as e:
    st.error(f"Błąd arkusza: {e}. Sprawdź nazwy zakładek!")
    st.stop()

# --- FUNKCJE POMOCNICZE ---

# TU JEST POPRAWKA NA SZYBKOŚĆ (TTL=5 sekund)
@st.cache_data(ttl=5)
def pobierz_dane(_worksheet):
    # _worksheet z podkreślnikiem, żeby Streamlit nie próbował go haszować
    if _worksheet is None:
        return pd.DataFrame()
    dane = _worksheet.get_all_records()
    df = pd.DataFrame(dane)
    # ZABEZPIECZENIE: Usuwamy spacje z nazw kolumn (np. "Koszt " -> "Koszt")
    if not df.empty:
        df.columns = df.columns.str.strip()
    return df

def zapisz_nowy_wiersz(worksheet, lista_wartosci):
    worksheet.append_row(lista_wartosci)
    st.cache_data.clear() # Czyścimy pamięć po dodaniu, żeby od razu widzieć zmianę

def aktualizuj_caly_arkusz(worksheet, df):
    worksheet.clear()
    worksheet.update([df.columns.values.tolist()] + df.values.tolist())
    st.cache_data.clear() # Czyścimy pamięć po edycji

# --- UI APLIKACJI ---
st.title("💍 Menadżer Ślubny")

tab1, tab2, tab3 = st.tabs(["👥 Lista Gości", "🎧 Organizacja", "✅ Lista Zadań"])

# ==========================
# ZAKŁADKA 1: GOŚCIE
# ==========================
with tab1:
    st.header("Zarządzanie Gośćmi")

    def obsluga_dodawania():
        imie = st.session_state.get("input_imie", "")
        partner = st.session_state.get("input_partner", "")
        rsvp = st.session_state.get("check_rsvp", False)
        plusone = st.session_state.get("check_plusone", False)
        invite = st.session_state.get("check_invite", False)

        if imie:
            r_txt = "Tak" if rsvp else "Nie"
            i_txt = "Tak" if invite else "Nie"
            zapisz_nowy_wiersz(worksheet_goscie, [imie, "", r_txt, i_txt])
            if plusone and partner:
                zapisz_nowy_wiersz(worksheet_goscie, [partner, f"(Osoba tow. dla: {imie})", r_txt, i_txt])
            
            st.toast(f"✅ Dodano: {imie}")
            # Reset
            st.session_state["input_imie"] = ""
            st.session_state["input_partner"] = ""
            st.session_state["check_rsvp"] = False
            st.session_state["check_plusone"] = False
            st.session_state["check_invite"] = False
        else:
            st.warning("Wpisz imię!")

    try:
        df_goscie = pobierz_dane(worksheet_goscie)
    except Exception as e:
        st.error(f"Błąd danych Goście: {e}")
        st.stop()
    
    if df_goscie.empty:
        df_goscie = pd.DataFrame(columns=["Imie_Nazwisko", "Imie_Osoby_Tow", "RSVP", "Zaproszenie_Wyslane"])
    
    # Zabezpieczenie przed brakiem kolumn
    for col in ["Imie_Nazwisko", "Imie_Osoby_Tow", "RSVP", "Zaproszenie_Wyslane"]:
        if col not in df_goscie.columns:
            df_goscie[col] = ""

    with st.expander("➕ Szybkie dodawanie", expanded=False):
        c_plus = st.checkbox("Chcę dodać osobę towarzyszącą (+1)", key="check_plusone")
        c1, c2 = st.columns(2)
        with c1: st.text_input("Imię i Nazwisko", key="input_imie")
        with c2: 
            if c_plus: st.text_input("Imię Osoby Tow.", key="input_partner")
        
        k1, k2 = st.columns(2)
        with k1: st.checkbox("✉️ Zaproszenie wysłane?", key="check_invite")
        with k2: st.checkbox("✅ Potwierdzenie (RSVP)", key="check_rsvp")
        
        st.button("Dodaj do listy", on_click=obsluga_dodawania, key="btn_goscie")

    st.write("---")
    st.subheader(f"📋 Lista Gości ({len(df_goscie)})")

    df_display = df_goscie.copy()
    # Konwersja danych do edycji
    df_display["Imie_Nazwisko"] = df_display["Imie_Nazwisko"].astype(str).replace("nan", "")
    df_display["Imie_Osoby_Tow"] = df_display["Imie_Osoby_Tow"].astype(str).replace("nan", "")
    
    def to_bool(x): return str(x).lower() in ["tak", "true", "1", "yes"]
    df_display["RSVP"] = df_display["RSVP"].apply(to_bool)
    df_display["Zaproszenie_Wyslane"] = df_display["Zaproszenie_Wyslane"].apply(to_bool)

    # Sortowanie
    c_s1, c_s2 = st.columns([1,3])
    with c_s1: st.write("Sortuj wg:")
    with c_s2:
        sort_g = st.radio("Sort", ["Domyślnie", "✉️ Wysłane", "✉️ Brak", "✅ RSVP", "🔤 A-Z"], horizontal=True, label_visibility="collapsed", key="sort_g")

    if sort_g == "✉️ Wysłane": df_display = df_display.sort_values("Zaproszenie_Wyslane", ascending=False)
    elif sort_g == "✉️ Brak": df_display = df_display.sort_values("Zaproszenie_Wyslane", ascending=True)
    elif sort_g == "✅ RSVP": df_display = df_display.sort_values("RSVP", ascending=False)
    elif sort_g == "🔤 A-Z": df_display = df_display.sort_values("Imie_Nazwisko", ascending=True)

    edytowane_goscie = st.data_editor(
        df_display, num_rows="dynamic", use_container_width=True, key="editor_goscie", hide_index=True,
        column_config={
            "Imie_Nazwisko": st.column_config.TextColumn("Imię i Nazwisko", required=True),
            "Imie_Osoby_Tow": st.column_config.TextColumn("Info (+1)", width="large"),
            "Zaproszenie_Wyslane": st.column_config.CheckboxColumn("✉️ Wysłane?"),
            "RSVP": st.column_config.CheckboxColumn("✅ RSVP")
        }
    )

    if st.button("💾 Zapisz zmiany (Goście)", key="save_goscie"):
        to_save = edytowane_goscie.copy()
        to_save = to_save[to_save["Imie_Nazwisko"].str.strip() != ""]
        to_save["RSVP"] = to_save["RSVP"].apply(lambda x: "Tak" if x else "Nie")
        to_save["Zaproszenie_Wyslane"] = to_save["Zaproszenie_Wyslane"].apply(lambda x: "Tak" if x else "Nie")
        aktualizuj_caly_arkusz(worksheet_goscie, to_save)
        st.success("Zapisano!")
        st.rerun()

    if not df_goscie.empty:
        stat_rsvp = len(df_goscie[df_goscie["RSVP"].apply(str).str.lower() == "tak"])
        stat_inv = len(df_goscie[df_goscie["Zaproszenie_Wyslane"].apply(str).str.lower() == "tak"])
        c1, c2, c3 = st.columns(3)
        c1.metric("Goście", len(df_goscie))
        c2.metric("Wysłane", stat_inv)
        c3.metric("Potwierdzone", stat_rsvp)

# ==========================
# ZAKŁADKA 2: ORGANIZACJA
# ==========================
with tab2:
    st.header("🎧 Organizacja i Budżet")

    def dodaj_usluge():
        rola = st.session_state.get("org_rola", "")
        koszt = st.session_state.get("org_koszt", 0.0)
        oplacone = st.session_state.get("org_oplacone", False)
        info = st.session_state.get("org_info", "")
        zaliczka = st.session_state.get("org_zaliczka_kwota", 0.0)
        zal_opl = st.session_state.get("org_zaliczka_oplacona", False)

        if rola:
            zapisz_nowy_wiersz(worksheet_obsluga, [
                rola, info, koszt, 
                "Tak" if oplacone else "Nie", 
                zaliczka, 
                "Tak" if zal_opl else "Nie"
            ])
            st.toast(f"💰 Dodano: {rola}")
            # Reset
            for k in ["org_rola", "org_info", "org_koszt", "org_oplacone", "org_zaliczka_kwota", "org_zaliczka_oplacona"]:
                if k in st.session_state: del st.session_state[k]
        else:
            st.warning("Wpisz Rolę!")

    try:
        df_obsluga = pobierz_dane(worksheet_obsluga)
    except Exception as e:
        st.error(f"Błąd danych Obsługa: {e}")
        st.stop()

    # ZABEZPIECZENIE PRZED BRAKIEM KOLUMN (Twój błąd KeyError)
    wymagane_kolumny = ["Rola", "Informacje", "Koszt", "Czy_Oplacone", "Zaliczka", "Czy_Zaliczka_Oplacona"]
    if df_obsluga.empty:
        df_obsluga = pd.DataFrame(columns=wymagane_kolumny)
    else:
        # Sprawdzamy czy kolumny istnieją. Jeśli nie - pokazujemy błąd zamiast crasha
        brakujace = [col for col in wymagane_kolumny if col not in df_obsluga.columns]
        if brakujace:
            st.error(f"🚨 BŁĄD ARKUSZA: Brakuje kolumn: {brakujace}. Sprawdź nagłówki w Google Sheets (zakładka Obsluga)!")
            st.write("Aktualnie widoczne kolumny:", df_obsluga.columns.tolist())
            st.stop()

    with st.expander("➕ Dodaj koszt", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            st.text_input("Rola", key="org_rola")
            st.number_input("Koszt", step=100.0, key="org_koszt")
            st.checkbox("Opłacone całe?", key="org_oplacone")
        with c2:
            st.text_input("Info", key="org_info")
            st.number_input("Zaliczka", step=100.0, key="org_zaliczka_kwota")
            st.checkbox("Zaliczka opłacona?", key="org_zaliczka_oplacona")
        st.button("Dodaj", on_click=dodaj_usluge, key="btn_obsluga")

    st.write("---")
    st.subheader(f"💸 Wydatki ({len(df_obsluga)})")

    df_org = df_obsluga.copy()
    # Konwersja
    df_org["Koszt"] = pd.to_numeric(df_org["Koszt"], errors='coerce').fillna(0.0)
    df_org["Zaliczka"] = pd.to_numeric(df_org["Zaliczka"], errors='coerce').fillna(0.0)
    df_org["Rola"] = df_org["Rola"].astype(str).replace("nan", "")
    df_org["Informacje"] = df_org["Informacje"].astype(str).replace("nan", "")
    df_org["Czy_Oplacone"] = df_org["Czy_Oplacone"].apply(to_bool)
    df_org["Czy_Zaliczka_Oplacona"] = df_org["Czy_Zaliczka_Oplacona"].apply(to_bool)

    c_s1, c_s2 = st.columns([1,3])
    with c_s1: st.write("Sortuj wg:")
    with c_s2:
        sort_o = st.radio("Sort", ["Domyślnie", "💰 Najdroższe", "❌ Nieopłacone", "✅ Opłacone", "❌ Brak Zaliczki", "✅ Zaliczka OK", "🔤 A-Z"], horizontal=True, label_visibility="collapsed", key="sort_o")

    if sort_o == "💰 Najdroższe": df_org = df_org.sort_values("Koszt", ascending=False)
    elif sort_o == "❌ Nieopłacone": df_org = df_org.sort_values("Czy_Oplacone", ascending=True)
    elif sort_o == "✅ Opłacone": df_org = df_org.sort_values("Czy_Oplacone", ascending=False)
    elif sort_o == "❌ Brak Zaliczki": df_org = df_org.sort_values("Czy_Zaliczka_Oplacona", ascending=True)
    elif sort_o == "✅ Zaliczka OK": df_org = df_org.sort_values("Czy_Zaliczka_Oplacona", ascending=False)
    elif sort_o == "🔤 A-Z": df_org = df_org.sort_values("Rola", ascending=True)

    edytowana_org = st.data_editor(
        df_org, num_rows="dynamic", use_container_width=True, key="editor_obsluga", hide_index=True,
        column_config={
            "Rola": st.column_config.TextColumn("Rola", required=True),
            "Koszt": st.column_config.NumberColumn("Koszt", format="%d zł"),
            "Zaliczka": st.column_config.NumberColumn("Zaliczka", format="%d zł"),
            "Czy_Oplacone": st.column_config.CheckboxColumn("✅ Opłacone?"),
            "Czy_Zaliczka_Oplacona": st.column_config.CheckboxColumn("✅ Zaliczka?")
        }
    )

    if st.button("💾 Zapisz zmiany (Budżet)", key="save_obsluga"):
        to_save = edytowana_org.copy()
        to_save = to_save[to_save["Rola"].str.strip() != ""]
        to_save["Czy_Oplacone"] = to_save["Czy_Oplacone"].apply(lambda x: "Tak" if x else "Nie")
        to_save["Czy_Zaliczka_Oplacona"] = to_save["Czy_Zaliczka_Oplacona"].apply(lambda x: "Tak" if x else "Nie")
        aktualizuj_caly_arkusz(worksheet_obsluga, to_save)
        st.success("Zapisano!")
        st.rerun()
    
    if not df_org.empty:
        total = df_org["Koszt"].sum()
        wydano = 0.0
        for i, r in df_org.iterrows():
            if r["Czy_Oplacone"]: wydano += r["Koszt"]
            elif r["Czy_Zaliczka_Oplacona"]: wydano += r["Zaliczka"]
        
        st.write("---")
        c1, c2, c3 = st.columns(3)
        c1.metric("Łącznie", f"{total:,.0f} zł")
        c2.metric("Wydano", f"{wydano:,.0f} zł")
        c3.metric("Pozostało", f"{total-wydano:,.0f} zł", delta=-(total-wydano), delta_color="inverse")

# ==========================
# ZAKŁADKA 3: ZADANIA
# ==========================
with tab3:
    st.header("✅ Co trzeba zrobić?")

    def dodaj_zadanie():
        tresc = st.session_state.get("todo_tresc", "")
        termin = st.session_state.get("todo_data", date.today())
        if tresc:
            zapisz_nowy_wiersz(worksheet_zadania, [tresc, termin.strftime("%Y-%m-%d"), "Nie"])
            st.toast("Dodano!")
            st.session_state["todo_tresc"] = ""
        else: st.warning("Wpisz treść")

    try:
        df_todo = pobierz_dane(worksheet_zadania)
    except:
        df_todo = pd.DataFrame(columns=["Zadanie", "Termin", "Czy_Zrobione"])
    
    if df_todo.empty:
         df_todo = pd.DataFrame(columns=["Zadanie", "Termin", "Czy_Zrobione"])

    with st.expander("➕ Dodaj zadanie", expanded=False):
        c1, c2 = st.columns([2,1])
        with c1: st.text_input("Treść", key="todo_tresc")
        with c2: st.date_input("Termin", key="todo_data")
        st.button("Dodaj", on_click=dodaj_zadanie, key="btn_todo")

    st.write("---")
    df_td = df_todo.copy()
    df_td["Zadanie"] = df_td["Zadanie"].astype(str).replace("nan", "")
    df_td["Termin"] = pd.to_datetime(df_td["Termin"], errors='coerce').dt.date
    df_td["Czy_Zrobione"] = df_td["Czy_Zrobione"].apply(to_bool)

    c_s1, c_s2 = st.columns([1,3])
    with c_s1: st.write("Sortuj wg:")
    with c_s2:
        sort_t = st.radio("Sort", ["Data", "Do zrobienia", "Zrobione", "A-Z"], horizontal=True, label_visibility="collapsed", key="sort_t")
    
    if sort_t == "Data": df_td = df_td.sort_values("Termin")
    elif sort_t == "Do zrobienia": df_td = df_td.sort_values("Czy_Zrobione", ascending=True)
    elif sort_t == "Zrobione": df_td = df_td.sort_values("Czy_Zrobione", ascending=False)
    elif sort_t == "A-Z": df_td = df_td.sort_values("Zadanie")

    edytowane_todo = st.data_editor(
        df_td, num_rows="dynamic", use_container_width=True, key="editor_todo", hide_index=True,
        column_config={
            "Zadanie": st.column_config.TextColumn("Treść", required=True, width="large"),
            "Termin": st.column_config.DateColumn("Termin", format="DD.MM.YYYY"),
            "Czy_Zrobione": st.column_config.CheckboxColumn("Zrobione?")
        }
    )

    if st.button("💾 Zapisz (Zadania)", key="save_todo"):
        to_save = edytowane_todo.copy()
        to_save = to_save[to_save["Zadanie"].str.strip() != ""]
        to_save["Termin"] = pd.to_datetime(to_save["Termin"]).dt.strftime("%Y-%m-%d")
        to_save["Czy_Zrobione"] = to_save["Czy_Zrobione"].apply(lambda x: "Tak" if x else "Nie")
        aktualizuj_caly_arkusz(worksheet_zadania, to_save)
        st.success("Zapisano!")
        st.rerun()

    if not df_td.empty:
        done = len(df_td[df_td["Czy_Zrobione"]])
        total = len(df_td)
        perc = int(done/total*100) if total > 0 else 0
        st.write("---")
        st.progress(perc, f"Postęp: {done}/{total} ({perc}%)")
        if perc == 100: st.balloons()
