import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import date
import matplotlib.pyplot as plt
import altair as alt
import numpy as np

# --- STAŁE ---
LISTA_KATEGORII_BAZA = [
    "Inne"
]

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
    try:
        worksheet_stoly = sh.worksheet("Stoly")
    except:
        worksheet_stoly = None
        st.warning("⚠️ Brakuje zakładki 'Stoly' w Arkuszu Google! Utwórz ją z nagłówkami: Numer, Ksztalt, Liczba_Miejsc, Goscie_Lista")

except Exception as e:
    st.error(f"Błąd arkusza: {e}.")
    st.stop()

# --- FUNKCJE POMOCNICZE ---

# WAŻNE: ttl=600 (10 minut) zapobiega błędowi "Quota exceeded" (APIError 429)
@st.cache_data(ttl=600)
def pobierz_dane(_worksheet):
    if _worksheet is None: return pd.DataFrame()
    dane = _worksheet.get_all_records()
    return pd.DataFrame(dane)

def zapisz_nowy_wiersz(worksheet, lista_wartosci):
    worksheet.append_row(lista_wartosci)
    st.cache_data.clear() # Czyści pamięć po zapisie, żeby widzieć zmiany natychmiast

def aktualizuj_caly_arkusz(worksheet, df):
    worksheet.clear()
    worksheet.update([df.columns.values.tolist()] + df.values.tolist())
    st.cache_data.clear() # Czyści pamięć po edycji

# --- UI APLIKACJI ---
st.title("💍 Menadżer Ślubny")

tab1, tab2, tab3, tab4 = st.tabs(["👥 Lista Gości", "🎧 Organizacja", "✅ Lista Zadań", "🍽️ Rozsadzanie Stołów"])

# ==========================
# ZAKŁADKA 1: GOŚCIE
# ==========================
with tab1:
    st.header("Zarządzanie Gośćmi")

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
            st.warning("Wpisz imię!")

    try:
        df_goscie = pobierz_dane(worksheet_goscie)
    except Exception as e:
        st.error(f"Błąd: {e}")
        st.stop()
    
    if df_goscie.empty:
        df_goscie = pd.DataFrame(columns=["Imie_Nazwisko", "Imie_Osoby_Tow", "RSVP", "Zaproszenie_Wyslane"])

    # ZABEZPIECZENIE KOLUMN
    df_goscie.columns = df_goscie.columns.str.strip() # Usuwamy spacje z nagłówków
    for col in ["Imie_Nazwisko", "Imie_Osoby_Tow", "RSVP", "Zaproszenie_Wyslane"]:
        if col not in df_goscie.columns:
            df_goscie[col] = "" # Tworzymy brakującą kolumnę

    with st.expander("➕ Szybkie dodawanie", expanded=False):
        czy_z_osoba = st.checkbox("Chcę dodać osobę towarzyszącą (+1)", key="check_plusone")
        c1, c2 = st.columns(2)
        with c1: st.text_input("Imię i Nazwisko", key="input_imie")
        with c2: 
            if czy_z_osoba: st.text_input("Imię Osoby Tow.", key="input_partner")
        k1, k2 = st.columns(2)
        with k1: st.checkbox("✉️ Zaproszenie wysłane?", key="check_invite")
        with k2: st.checkbox("✅ Potwierdzenie (RSVP)", key="check_rsvp")
        st.button("Dodaj do listy", on_click=obsluga_dodawania, key="btn_goscie")

    st.write("---")
    st.subheader(f"📋 Lista Gości ({len(df_goscie)})")

    df_display = df_goscie.copy()
    if not df_display.empty:
        df_display["Imie_Nazwisko"] = df_display["Imie_Nazwisko"].astype(str).replace("nan", "")
        df_display["Imie_Osoby_Tow"] = df_display["Imie_Osoby_Tow"].astype(str).replace("nan", "")
        def parsuj_bool(x): return str(x).lower() in ["tak", "true", "1", "yes"]
        df_display["RSVP"] = df_display["RSVP"].apply(parsuj_bool)
        df_display["Zaproszenie_Wyslane"] = df_display["Zaproszenie_Wyslane"].apply(parsuj_bool)

        c1, c2 = st.columns([1,3])
        with c1: st.write("Sortuj:")
        with c2:
            sort_g = st.radio("Sort", ["Domyślnie", "✉️ Wysłane", "✉️ Brak", "✅ RSVP", "🔤 A-Z"], horizontal=True, label_visibility="collapsed", key="sort_g")
        
        if sort_g == "✉️ Wysłane": df_display = df_display.sort_values("Zaproszenie_Wyslane", ascending=False)
        elif sort_g == "✉️ Brak": df_display = df_display.sort_values("Zaproszenie_Wyslane", ascending=True)
        elif sort_g == "✅ RSVP": df_display = df_display.sort_values("RSVP", ascending=False)
        elif sort_g == "🔤 A-Z": df_display = df_display.sort_values("Imie_Nazwisko", ascending=True)

    edytowane_goscie = st.data_editor(
        df_display, num_rows="dynamic", use_container_width=True, hide_index=True, key="editor_goscie",
        column_config={
            "Imie_Nazwisko": st.column_config.TextColumn("Imię i Nazwisko", required=True),
            "Imie_Osoby_Tow": st.column_config.TextColumn("Info (+1)", width="large"),
            "Zaproszenie_Wyslane": st.column_config.CheckboxColumn("✉️ Wysłane?"),
            "RSVP": st.column_config.CheckboxColumn("✅ RSVP")
        }
    )

    if st.button("💾 Zapisz zmiany", key="save_goscie"):
        to_save = edytowane_goscie.copy()
        if not to_save.empty:
            to_save = to_save[to_save["Imie_Nazwisko"].str.strip() != ""]
            to_save["RSVP"] = to_save["RSVP"].apply(lambda x: "Tak" if x else "Nie")
            to_save["Zaproszenie_Wyslane"] = to_save["Zaproszenie_Wyslane"].apply(lambda x: "Tak" if x else "Nie")
        to_save = to_save.fillna("")
        aktualizuj_caly_arkusz(worksheet_goscie, to_save)
        st.success("Zapisano!")
        st.rerun()

    if not df_goscie.empty:
        conf = len(df_goscie[df_goscie["RSVP"].astype(str) == "Tak"])
        inv = len(df_goscie[df_goscie["Zaproszenie_Wyslane"].astype(str) == "Tak"])
        k1, k2, k3 = st.columns(3)
        k1.metric("Goście", len(df_goscie))
        k2.metric("Wysłane", inv)
        k3.metric("Potwierdzone", conf)

# ==========================
# ZAKŁADKA 2: ORGANIZACJA
# ==========================
with tab2:
    st.header("🎧 Organizacja i Budżet")

    try:
        df_obsluga = pobierz_dane(worksheet_obsluga)
    except:
        st.error("Błąd danych.")
        st.stop()

    org_cols = ["Kategoria", "Rola", "Informacje", "Koszt", "Czy_Oplacone", "Zaliczka", "Czy_Zaliczka_Oplacona"]
    if df_obsluga.empty: df_obsluga = pd.DataFrame(columns=org_cols)
    
    # ZABEZPIECZENIE KOLUMN
    df_obsluga.columns = df_obsluga.columns.str.strip()
    for c in org_cols:
        if c not in df_obsluga.columns:
            df_obsluga[c] = ""
            if c == "Kategoria": df_obsluga[c] = "Inne"

    # Logika kategorii
    base_cats = ["Sala i Jedzenie", "Muzyka", "Foto/Video", "Stroje", "Dekoracje", "Transport", "Inne"]
    if not df_obsluga.empty:
        curr = df_obsluga["Kategoria"].unique().tolist()
        all_cats = sorted(list(set(base_cats + [x for x in curr if str(x).strip() != ""])))
    else: all_cats = sorted(base_cats)
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
            zapisz_nowy_wiersz(worksheet_obsluga, [fin_cat, r, i, k, "Tak" if op else "Nie", z, "Tak" if z_op else "Nie"])
            st.toast(f"💰 Dodano: {r}")
            st.session_state["org_rola"] = ""
            st.session_state["org_info"] = ""
            st.session_state["org_koszt"] = 0.0
            st.session_state["org_op"] = False
            st.session_state["org_zal"] = 0.0
            st.session_state["org_z_op"] = False
            st.session_state["org_k_inp"] = ""
        else: st.warning("Wpisz Rolę i Kategorię")

    with st.expander("➕ Dodaj koszt", expanded=False):
        c1, c2 = st.columns(2)
        with c1: 
            sel = st.selectbox("Kategoria", select_opts, key="org_k_sel")
        with c2:
            if sel == "➕ Stwórz nową...": st.text_input("Nowa nazwa:", key="org_k_inp")
        
        st.text_input("Rola", key="org_rola")
        c1, c2 = st.columns(2)
        with c1:
            st.number_input("Koszt", step=100.0, key="org_koszt")
            st.checkbox("Opłacone całe?", key="org_op")
        with c2:
            st.text_input("Info", key="org_info")
            st.number_input("Zaliczka", step=100.0, key="org_zal")
            st.checkbox("Zaliczka opłacona?", key="org_z_op")
        st.button("Dodaj", on_click=dodaj_usluge, key="btn_org")

    st.write("---")
    st.subheader(f"💸 Wydatki ({len(df_obsluga)})")
    
    fil = st.multiselect("🔍 Filtruj:", all_cats)
    df_disp = df_obsluga.copy()
    if fil: df_disp = df_disp[df_disp["Kategoria"].isin(fil)]

    df_disp["Koszt"] = pd.to_numeric(df_disp["Koszt"], errors='coerce').fillna(0.0)
    df_disp["Zaliczka"] = pd.to_numeric(df_disp["Zaliczka"], errors='coerce').fillna(0.0)
    def fix_bool(x): return str(x).lower().strip() in ["tak", "true", "1", "yes"]
    df_disp["Czy_Oplacone"] = df_disp["Czy_Oplacone"].apply(fix_bool)
    df_disp["Czy_Zaliczka_Oplacona"] = df_disp["Czy_Zaliczka_Oplacona"].apply(fix_bool)

    c1, c2 = st.columns([1,3])
    with c1: st.write("Sortuj:")
    with c2:
        s = st.radio("S", ["Domyślnie", "💰 Najdroższe", "❌ Nieopłacone", "✅ Opłacone"], horizontal=True, label_visibility="collapsed", key="sort_org")
    
    if s == "💰 Najdroższe": df_disp = df_disp.sort_values("Koszt", ascending=False)
    elif s == "❌ Nieopłacone": df_disp = df_disp.sort_values("Czy_Oplacone", ascending=True)
    elif s == "✅ Opłacone": df_disp = df_disp.sort_values("Czy_Oplacone", ascending=False)

    edited_org = st.data_editor(
        df_disp, num_rows="dynamic", use_container_width=True, hide_index=True, key="ed_org",
        column_config={
            "Kategoria": st.column_config.SelectboxColumn("Kategoria", options=all_cats, required=True),
            "Rola": st.column_config.TextColumn("Rola", required=True),
            "Koszt": st.column_config.NumberColumn("Koszt", format="%d zł"),
            "Czy_Oplacone": st.column_config.CheckboxColumn("✅ Opłacone?"),
            "Zaliczka": st.column_config.NumberColumn("Zaliczka", format="%d zł"),
            "Czy_Zaliczka_Oplacona": st.column_config.CheckboxColumn("✅ Zaliczka?")
        }
    )

    if st.button("💾 Zapisz (Budżet)", key="sav_org"):
        to_save = edited_org.copy()
        if not to_save.empty:
            to_save = to_save[to_save["Rola"].str.strip() != ""]
            to_save["Czy_Oplacone"] = to_save["Czy_Oplacone"].apply(lambda x: "Tak" if x else "Nie")
            to_save["Czy_Zaliczka_Oplacona"] = to_save["Czy_Zaliczka_Oplacona"].apply(lambda x: "Tak" if x else "Nie")
        to_save = to_save.fillna("")
        aktualizuj_caly_arkusz(worksheet_obsluga, to_save)
        st.success("Zapisano!")
        st.rerun()

    if not df_obsluga.empty:
        calc = df_obsluga.copy()
        calc["Koszt"] = pd.to_numeric(calc["Koszt"], errors='coerce').fillna(0.0)
        calc["Zaliczka"] = pd.to_numeric(calc["Zaliczka"], errors='coerce').fillna(0.0)
        total = calc["Koszt"].sum()
        paid = 0.0
        for i, r in calc.iterrows():
            if fix_bool(r["Czy_Oplacone"]): paid += r["Koszt"]
            elif fix_bool(r["Czy_Zaliczka_Oplacona"]): paid += r["Zaliczka"]
        
        st.write("---")
        c1, c2, c3 = st.columns(3)
        c1.metric("Łącznie", f"{total:,.0f} zł")
        c2.metric("Zapłacono", f"{paid:,.0f} zł")
        c3.metric("Do zapłaty", f"{total-paid:,.0f} zł", delta=-(total-paid), delta_color="inverse")

        st.write("---")
        st.subheader("📊 Struktura Wydatków")
        grp = calc.groupby("Kategoria")["Koszt"].sum().reset_index().sort_values("Koszt", ascending=False)
        grp = grp[grp["Koszt"] > 0]

        if not grp.empty:
            st.write("**Ile wydajemy na co? (w zł)**")
            chart = alt.Chart(grp).mark_bar().encode(
                x=alt.X('Koszt', title='Kwota (zł)'),
                y=alt.Y('Kategoria', sort='-x', title='Kategoria'),
                color=alt.Color('Kategoria', legend=None),
                tooltip=['Kategoria', alt.Tooltip('Koszt', format=',.0f')]
            ).properties(
                height=300
            ).interactive()
            st.altair_chart(chart, use_container_width=True)

            st.write("---")
            st.write("**Udział procentowy**")
            
            # Matplotlib Pie Chart
            fig, ax = plt.subplots(figsize=(6, 6))
            wedges, texts, autotexts = ax.pie(
                grp["Koszt"], 
                labels=grp["Kategoria"], 
                autopct='%1.1f%%', 
                startangle=90, 
                textprops={'color':"white", 'fontsize': 10}
            )
            plt.setp(autotexts, size=10, weight="bold", color="white")
            plt.setp(texts, size=10, color="white")
            fig.patch.set_alpha(0)
            ax.patch.set_alpha(0)
            ax.axis('equal')
            
            c_center = st.columns([1,2,1])
            with c_center[1]:
                st.pyplot(fig, use_container_width=True)

# ==========================
# ZAKŁADKA 3: ZADANIA
# ==========================
with tab3:
    st.header("✅ Co trzeba zrobić?")
    def dodaj_todo():
        t = st.session_state.get("todo_t", "")
        d = st.session_state.get("todo_d", date.today())
        if t:
            zapisz_nowy_wiersz(worksheet_zadania, [t, d.strftime("%Y-%m-%d"), "Nie"])
            st.toast("Dodano!")
            st.session_state["todo_t"] = ""
        else: st.warning("Wpisz treść")

    try: df_todo = pobierz_dane(worksheet_zadania)
    except: df_todo = pd.DataFrame(columns=["Zadanie", "Termin", "Czy_Zrobione"])
    
    # --- NAPRAWA BŁĘDU KEYERROR: ZABEZPIECZENIE KOLUMN ---
    # Upewniamy się, że nazwy kolumn nie mają spacji
    if not df_todo.empty:
        df_todo.columns = df_todo.columns.str.strip()
    
    # Upewniamy się, że wszystkie wymagane kolumny istnieją
    cols_todo = ["Zadanie", "Termin", "Czy_Zrobione"]
    for c in cols_todo:
        if c not in df_todo.columns: 
            df_todo[c] = ""
    # -----------------------------------------------------

    with st.expander("➕ Dodaj zadanie", expanded=False):
        c1, c2 = st.columns([2,1])
        with c1: st.text_input("Treść", key="todo_t")
        with c2: st.date_input("Termin", key="todo_d")
        st.button("Dodaj", on_click=dodaj_todo, key="btn_todo")

    st.write("---")
    df_td = df_todo.copy()
    
    # Bezpieczna konwersja (kolumny na pewno istnieją dzięki zabezpieczeniu wyżej)
    df_td["Zadanie"] = df_td["Zadanie"].astype(str).replace("nan", "")
    df_td["Termin"] = pd.to_datetime(df_td["Termin"], errors='coerce').dt.date
    df_td["Czy_Zrobione"] = df_td["Czy_Zrobione"].apply(lambda x: str(x).lower() in ["tak", "true", "1"])

    c1, c2 = st.columns([1,3])
    with c1: st.write("Sortuj:")
    with c2:
        s_t = st.radio("S_T", ["Data", "Do zrobienia", "Zrobione"], horizontal=True, label_visibility="collapsed", key="s_t")
    
    if not df_td.empty:
        if s_t == "Data": df_td = df_td.sort_values("Termin")
        elif s_t == "Do zrobienia": df_td = df_td.sort_values("Czy_Zrobione", ascending=True)
        elif s_t == "Zrobione": df_td = df_td.sort_values("Czy_Zrobione", ascending=False)

    ed_todo = st.data_editor(
        df_td, num_rows="dynamic", use_container_width=True, hide_index=True, key="ed_todo",
        column_config={
            "Zadanie": st.column_config.TextColumn("Treść", required=True, width="large"),
            "Termin": st.column_config.DateColumn("Termin", format="DD.MM.YYYY"),
            "Czy_Zrobione": st.column_config.CheckboxColumn("Zrobione?")
        }
    )

    if st.button("💾 Zapisz (Zadania)", key="sav_todo"):
        to_s = ed_todo.copy()
        if not to_s.empty:
            to_s = to_s[to_s["Zadanie"].str.strip() != ""]
            to_s["Termin"] = pd.to_datetime(to_s["Termin"]).dt.strftime("%Y-%m-%d")
            to_s["Czy_Zrobione"] = to_s["Czy_Zrobione"].apply(lambda x: "Tak" if x else "Nie")
        to_s = to_s.fillna("")
        aktualizuj_caly_arkusz(worksheet_zadania, to_s)
        st.success("Zapisano!")
        st.rerun()

    if not df_td.empty:
        done = len(df_td[df_td["Czy_Zrobione"]])
        total = len(df_td)
        p = int(done/total*100) if total > 0 else 0
        st.write("---")
        st.progress(p, f"Postęp: {done}/{total} ({p}%)")
        if p == 100: st.balloons()

# ==========================
# ZAKŁADKA 4: STOŁY
# ==========================
with tab4:
    st.header("🍽️ Rozsadzanie Gości przy Stołach")

    # 1. Pobieramy dane stołów
    try:
        df_stoly = pobierz_dane(worksheet_stoly)
    except Exception as e:
        st.error("Problem z zakładką 'Stoly'. Sprawdź czy istnieje.")
        st.stop()

    # Zabezpieczenie kolumn
    cols_stoly = ["Numer", "Ksztalt", "Liczba_Miejsc", "Goscie_Lista"]
    if df_stoly.empty:
        df_stoly = pd.DataFrame(columns=cols_stoly)
    
    # ZABEZPIECZENIE: Usuwamy spacje i tworzymy brakujące kolumny
    df_stoly.columns = df_stoly.columns.str.strip()
    for c in cols_stoly:
        if c not in df_stoly.columns: df_stoly[c] = ""

    # Konwersja danych
    df_stoly["Numer"] = df_stoly["Numer"].astype(str)
    df_stoly["Liczba_Miejsc"] = pd.to_numeric(df_stoly["Liczba_Miejsc"], errors='coerce').fillna(0).astype(int)

    # --- KOLUMNA LEWA: LISTA I DODAWANIE ---
    col_left, col_right = st.columns([1, 2])

    with col_left:
        st.subheader("➕ Dodaj Stół")
        with st.form("dodaj_stol_form"):
            nr_stolu = st.text_input("Numer/Nazwa Stołu", placeholder="np. Stół 1 lub Wiejski")
            ksztalt = st.selectbox("Kształt", ["Okrągły", "Prostokątny"])
            miejsca = st.number_input("Liczba Miejsc", min_value=1, max_value=24, value=8)
            submitted = st.form_submit_button("Dodaj Stół")
            
            if submitted and nr_stolu:
                # Goscie_Lista to będzie string z imionami oddzielonymi średnikiem
                pusta_lista = ";".join(["" for _ in range(miejsca)])
                zapisz_nowy_wiersz(worksheet_stoly, [nr_stolu, ksztalt, miejsca, pusta_lista])
                st.toast(f"Dodano stół: {nr_stolu}")
                st.rerun()

        st.write("---")
        st.subheader("📋 Lista Stołów")
        
        # Wybór stołu do edycji
        if not df_stoly.empty:
            list_of_tables = df_stoly["Numer"].tolist()
            wybrany_stol_id = st.radio("Wybierz stół do edycji:", list_of_tables)
        else:
            wybrany_stol_id = None
            st.info("Brak stołów. Dodaj pierwszy!")

    # --- KOLUMNA PRAWA: EDYCJA I WIZUALIZACJA ---
    with col_right:
        if wybrany_stol_id:
            st.subheader(f"Edycja: {wybrany_stol_id}")
            
            # Pobieramy dane wybranego stołu
            row = df_stoly[df_stoly["Numer"] == wybrany_stol_id].iloc[0]
            max_miejsc = int(row["Liczba_Miejsc"])
            ksztalt_stolu = row["Ksztalt"]
            
            # Parsowanie listy gości (rozdzielone średnikami)
            obecni_goscie_str = str(row["Goscie_Lista"])
            if ";" in obecni_goscie_str:
                lista_gosci = obecni_goscie_str.split(";")
            else:
                lista_gosci = [""] * max_miejsc
            
            if len(lista_gosci) < max_miejsc:
                lista_gosci += [""] * (max_miejsc - len(lista_gosci))
            lista_gosci = lista_gosci[:max_miejsc]

            # --- FORMULARZ ROZSADZANIA ---
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
                    
                    # Konwersja na int (naprawa błędu JSON)
                    idx = int(df_stoly[df_stoly["Numer"] == wybrany_stol_id].index[0] + 2)
                    
                    worksheet_stoly.update_cell(idx, 4, zapis_string)
                    st.cache_data.clear()
                    st.success("Zapisano gości!")
                    st.rerun()

            # --- WIZUALIZACJA ---
            st.write("---")
            st.write(f"**Podgląd: {ksztalt_stolu} ({max_miejsc} os.)**")
            
            fig, ax = plt.subplots(figsize=(6, 6))
            ax.set_aspect('equal')
            ax.axis('off')

            table_color = '#e0e0e0'
            seat_color = '#4CAF50'
            text_color = 'black'

            if ksztalt_stolu == "Okrągły":
                circle = plt.Circle((0, 0), 0.6, color=table_color, ec='black')
                ax.add_artist(circle)
                ax.text(0, 0, wybrany_stol_id, ha='center', va='center', fontsize=12, fontweight='bold')

                for i in range(max_miejsc):
                    angle = 2 * np.pi * i / max_miejsc
                    x = 0.85 * np.cos(angle)
                    y = 0.85 * np.sin(angle)
                    
                    seat = plt.Circle((x, y), 0.1, color=seat_color, alpha=0.7)
                    ax.add_artist(seat)
                    
                    guest_name = nowa_lista_gosci[i]
                    text_x = 1.1 * np.cos(angle)
                    text_y = 1.1 * np.sin(angle)
                    
                    rot = np.degrees(angle)
                    if 90 < rot < 270:
                        rot += 180
                        ha = 'right'
                    else:
                        ha = 'left'

                    if guest_name:
                        ax.text(text_x, text_y, guest_name, ha=ha, va='center', rotation=rot, fontsize=9)
                    else:
                        ax.text(text_x, text_y, str(i+1), ha=ha, va='center', rotation=rot, fontsize=8, color='grey')

                ax.set_xlim(-1.5, 1.5)
                ax.set_ylim(-1.5, 1.5)

            elif ksztalt_stolu == "Prostokątny":
                rect = plt.Rectangle((-0.5, -1), 1, 2, color=table_color, ec='black')
                ax.add_artist(rect)
                ax.text(0, 0, wybrany_stol_id, ha='center', va='center', rotation=90, fontsize=12, fontweight='bold')

                side_count = (max_miejsc + 1) // 2
                
                for i in range(max_miejsc):
                    guest_name = nowa_lista_gosci[i]
                    
                    if i < side_count:
                        x = -0.7
                        y = np.linspace(-0.8, 0.8, side_count)[i]
                        ha = 'right'
                    else:
                        x = 0.7
                        y = np.linspace(-0.8, 0.8, max_miejsc - side_count)[i - side_count]
                        ha = 'left'

                    seat = plt.Circle((x if x>0 else x+0.1, y), 0.1, color=seat_color, alpha=0.7)
                    if i < side_count: seat.center = (-0.6, y)
                    else: seat.center = (0.6, y)
                    
                    ax.add_artist(seat)

                    if guest_name:
                        ax.text(x, y, guest_name, ha=ha, va='center', fontsize=9)
                    else:
                        ax.text(x, y, str(i+1), ha=ha, va='center', fontsize=8, color='grey')

                ax.set_xlim(-1.5, 1.5)
                ax.set_ylim(-1.5, 1.5)

            st.pyplot(fig, use_container_width=True)
            
            st.write("---")
            if st.button("🗑️ Usuń ten stół"):
                # Konwersja na int (naprawa błędu JSON)
                idx = int(df_stoly[df_stoly["Numer"] == wybrany_stol_id].index[0] + 2)
                worksheet_stoly.delete_rows(idx)
                st.cache_data.clear()
                st.warning("Usunięto stół!")
                st.rerun()
