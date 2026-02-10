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

        st.error(f"⚠️ Nie znaleziono arkusza 'Wesele_Baza'. Upewnij się, że nazwa jest poprawna i udostępniłeś go mailowi robota.")

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

def pobierz_dane(_worksheet):

    dane = _worksheet.get_all_records()

    return pd.DataFrame(dane)



def zapisz_nowy_wiersz(worksheet, lista_wartosci):

    worksheet.append_row(lista_wartosci)

    st.cache_data.clear() 



def aktualizuj_caly_arkusz(worksheet, df):

    worksheet.clear()

    worksheet.update([df.columns.values.tolist()] + df.values.tolist())

    st.cache_data.clear()



# --- UI APLIKACJI ---

st.title("💍 Menadżer Ślubny")

tab1, tab2, tab3, tab4 = st.tabs(["👥 Lista Gości", "🎧 Organizacja", "✅ Lista Zadań", "🍽️ Rozplanowanie Stołów"])



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



    # 1. Pobranie danych

    try:

        df_obsluga = pobierz_dane(worksheet_obsluga)

    except Exception as e:

        st.error("Błąd danych. Sprawdź nagłówki w zakładce Obsluga.")

        st.stop()



    # 2. Definicja kolumn i struktury

    wymagane_kolumny_org = ["Kategoria", "Rola", "Informacje", "Koszt", "Czy_Oplacone", "Zaliczka", "Czy_Zaliczka_Oplacona"]

    

    if df_obsluga.empty:

        df_obsluga = pd.DataFrame(columns=wymagane_kolumny_org)



    # Zabezpieczenie nazw kolumn

    df_obsluga.columns = df_obsluga.columns.str.strip()

    for col in wymagane_kolumny_org:

        if col not in df_obsluga.columns:

            df_obsluga[col] = ""

            if col == "Kategoria": df_obsluga[col] = "Inne"



    # --- LOGIKA DYNAMICZNYCH KATEGORII ---

    baza_kategorii = [

        "Inne"

    ]

    

    if not df_obsluga.empty:

        obecne_w_arkuszu = df_obsluga["Kategoria"].unique().tolist()

        wszystkie_kategorie = sorted(list(set(baza_kategorii + [x for x in obecne_w_arkuszu if str(x).strip() != ""])))

    else:

        wszystkie_kategorie = sorted(baza_kategorii)



    opcje_do_wyboru = wszystkie_kategorie + ["➕ Stwórz nową kategorię..."]



    # --- FUNKCJA DODAWANIA ---

    def dodaj_usluge():

        wybor = st.session_state.get("org_kategoria_select")

        nowa_kat = st.session_state.get("org_kategoria_input", "")

        

        if wybor == "➕ Stwórz nową kategorię...":

            kategoria_finalna = nowa_kat.strip()

        else:

            kategoria_finalna = wybor



        rola = st.session_state.get("org_rola", "")

        info = st.session_state.get("org_info", "")

        koszt = st.session_state.get("org_koszt", 0.0)

        czy_oplacone = st.session_state.get("org_oplacone", False)

        zaliczka_kwota = st.session_state.get("org_zaliczka_kwota", 0.0)

        czy_zaliczka_oplacona = st.session_state.get("org_zaliczka_oplacona", False)



        if rola and kategoria_finalna:

            txt_oplacone = "Tak" if czy_oplacone else "Nie"

            txt_zaliczka_opl = "Tak" if czy_zaliczka_oplacona else "Nie"



            zapisz_nowy_wiersz(worksheet_obsluga, [kategoria_finalna, rola, info, koszt, txt_oplacone, zaliczka_kwota, txt_zaliczka_opl])

            st.toast(f"💰 Dodano: {rola} ({kategoria_finalna})")



            st.session_state["org_rola"] = ""

            st.session_state["org_info"] = ""

            st.session_state["org_koszt"] = 0.0

            st.session_state["org_oplacone"] = False

            st.session_state["org_zaliczka_kwota"] = 0.0

            st.session_state["org_zaliczka_oplacona"] = False

            st.session_state["org_kategoria_input"] = "" 

        else:

            st.warning("Musisz wpisać nazwę Roli i wybrać Kategorię!")



    # --- 1. Formularz Dodawania ---

    with st.expander("➕ Dodaj nową usługę / koszt", expanded=False):

        c_select, c_input = st.columns(2)

        with c_select:

            wybrana_opcja = st.selectbox("Kategoria", options=opcje_do_wyboru, key="org_kategoria_select")

        with c_input:

            if wybrana_opcja == "➕ Stwórz nową kategorię...":

                st.text_input("Wpisz nazwę nowej kategorii:", key="org_kategoria_input", placeholder="np. Poprawiny")

        

        st.text_input("Rola (np. DJ, Sala)", key="org_rola")

            

        c1, c2 = st.columns(2)

        with c1:

            st.number_input("Całkowity Koszt (zł)", min_value=0.0, step=100.0, key="org_koszt")

            st.checkbox("Czy całość już opłacona?", key="org_oplacone")

        with c2:

            st.text_input("Informacje dodatkowe (Kontakt)", key="org_info")

            st.number_input("Wymagana Zaliczka (0 jeśli brak)", min_value=0.0, step=100.0, key="org_zaliczka_kwota")

            st.checkbox("Czy zaliczka opłacona?", key="org_zaliczka_oplacona")

        

        st.button("Dodaj do budżetu", on_click=dodaj_usluge, key="btn_obsluga")



    # --- 2. FILTROWANIE I TABELA ---

    st.write("---")

    st.subheader(f"💸 Lista Wydatków ({len(df_obsluga)} pozycji)")

    

    lista_do_filtra = wszystkie_kategorie

    wybrane_kategorie = st.multiselect("🔍 Filtruj po kategorii:", options=lista_do_filtra, default=[])



    df_org_display = df_obsluga.copy()



    if wybrane_kategorie:

        df_org_display = df_org_display[df_org_display["Kategoria"].isin(wybrane_kategorie)]



    df_org_display["Koszt"] = pd.to_numeric(df_org_display["Koszt"], errors='coerce').fillna(0.0)

    df_org_display["Zaliczka"] = pd.to_numeric(df_org_display["Zaliczka"], errors='coerce').fillna(0.0)

    df_org_display["Rola"] = df_org_display["Rola"].astype(str).replace("nan", "")

    df_org_display["Kategoria"] = df_org_display["Kategoria"].astype(str).replace("nan", "")

    df_org_display["Informacje"] = df_org_display["Informacje"].astype(str).replace("nan", "")



    def napraw_booleana(x):

        return str(x).lower().strip() in ["tak", "true", "1", "yes"]



    df_org_display["Czy_Oplacone"] = df_org_display["Czy_Oplacone"].apply(napraw_booleana)

    df_org_display["Czy_Zaliczka_Oplacona"] = df_org_display["Czy_Zaliczka_Oplacona"].apply(napraw_booleana)



    col_sort1, col_sort2 = st.columns([1, 3])

    with col_sort1: st.write("**Sortuj wg:**")

    with col_sort2:

        tryb_finanse = st.radio("Sortowanie Finansów",

            options=["Domyślnie", "💰 Najdroższe", "❌ Nieopłacone", "✅ Opłacone", "❌ Brak Zaliczki", "✅ Zaliczka Opłacona"],

            label_visibility="collapsed", horizontal=True, key="sort_finanse")



    if tryb_finanse == "💰 Najdroższe": df_org_display = df_org_display.sort_values(by="Koszt", ascending=False)

    elif tryb_finanse == "❌ Nieopłacone": df_org_display = df_org_display.sort_values(by="Czy_Oplacone", ascending=True)

    elif tryb_finanse == "✅ Opłacone": df_org_display = df_org_display.sort_values(by="Czy_Oplacone", ascending=False)

    elif tryb_finanse == "❌ Brak Zaliczki": df_org_display = df_org_display.sort_values(by="Czy_Zaliczka_Oplacona", ascending=True)

    elif tryb_finanse == "✅ Zaliczka Opłacona": df_org_display = df_org_display.sort_values(by="Czy_Zaliczka_Oplacona", ascending=False)



    edytowane_obsluga = st.data_editor(

        df_org_display,

        num_rows="dynamic",

        column_config={

            "Kategoria": st.column_config.SelectboxColumn("Kategoria", options=wszystkie_kategorie, required=True, width="medium"),

            "Rola": st.column_config.TextColumn("Rola / Usługa", required=True),

            "Informacje": st.column_config.TextColumn("Kontakt / Info", width="medium"),

            "Koszt": st.column_config.NumberColumn("Koszt (Całość)", format="%d zł", step=100),

            "Czy_Oplacone": st.column_config.CheckboxColumn("✅ Opłacone?"),

            "Zaliczka": st.column_config.NumberColumn("Zaliczka", format="%d zł", step=100),

            "Czy_Zaliczka_Oplacona": st.column_config.CheckboxColumn("✅ Zaliczka?")

        },

        use_container_width=True,

        hide_index=True,

        key="editor_obsluga"

    )



    if st.button("💾 Zapisz zmiany", key="save_obsluga"):

        df_to_save_org = edytowane_obsluga.copy()

        if not df_to_save_org.empty:

            df_to_save_org = df_to_save_org[df_to_save_org["Rola"].str.strip() != ""]

            df_to_save_org["Czy_Oplacone"] = df_to_save_org["Czy_Oplacone"].apply(lambda x: "Tak" if x else "Nie")

            df_to_save_org["Czy_Zaliczka_Oplacona"] = df_to_save_org["Czy_Zaliczka_Oplacona"].apply(lambda x: "Tak" if x else "Nie")

        

        df_to_save_org = df_to_save_org.fillna("")

        aktualizuj_caly_arkusz(worksheet_obsluga, df_to_save_org)

        st.success("Zapisano budżet!")

        st.rerun()



        # --- WYKRESY ---

if not df_obsluga.empty:

        df_calc = df_obsluga.copy()

        df_calc["Koszt"] = pd.to_numeric(df_calc["Koszt"], errors='coerce').fillna(0.0)

        df_calc["Zaliczka"] = pd.to_numeric(df_calc["Zaliczka"], errors='coerce').fillna(0.0)

        def fix_bool(x): return str(x).lower().strip() in ["tak", "true", "1", "yes"]

        df_calc["Czy_Oplacone_Bool"] = df_calc["Czy_Oplacone"].apply(fix_bool)

        df_calc["Czy_Zaliczka_Bool"] = df_calc["Czy_Zaliczka_Oplacona"].apply(fix_bool)

        

        st.write("---")

        

        total_koszt = df_calc["Koszt"].sum()

        wydano = 0.0

        for index, row in df_calc.iterrows():

            if row["Czy_Oplacone_Bool"]:

                wydano += row["Koszt"]

            elif row["Czy_Zaliczka_Bool"]:

                wydano += row["Zaliczka"]

        

        pozostalo = total_koszt - wydano

        

        k1, k2, k3 = st.columns(3)

        k1.metric("Łączny budżet (Całość)", f"{total_koszt:,.0f} zł".replace(",", " "))

        k2.metric("Już zapłacono", f"{wydano:,.0f} zł".replace(",", " "))

        k3.metric("Pozostało do zapłaty", f"{pozostalo:,.0f} zł".replace(",", " "), delta=f"-{pozostalo} zł", delta_color="inverse")



        # --- WYKRESY (ALTAIR + MATPLOTLIB) ---

        st.write("---")

        st.subheader("📊 Struktura Wydatków")



        koszty_wg_kategorii = df_calc.groupby("Kategoria")["Koszt"].sum().reset_index()

        koszty_wg_kategorii = koszty_wg_kategorii.sort_values(by="Koszt", ascending=False)

        koszty_wg_kategorii = koszty_wg_kategorii[koszty_wg_kategorii["Koszt"] > 0]



        if not koszty_wg_kategorii.empty:

            # 1. Wykres Słupkowy (Altair)

            st.write("**Ile wydajemy na co? (w zł)**")

            

            chart_bar = alt.Chart(koszty_wg_kategorii).mark_bar().encode(

                x=alt.X('Koszt', title='Kwota (zł)'),

                y=alt.Y('Kategoria', sort='-x', title='Kategoria'),

                color=alt.Color('Kategoria', legend=None),

                tooltip=['Kategoria', alt.Tooltip('Koszt', format=',.0f')]

            ).properties(

                height=300

            ).interactive()

            

            st.altair_chart(chart_bar, use_container_width=True)



            st.write("---")



            # 2. Wykres Kołowy (Matplotlib)

            st.write("**Udział procentowy**")

            

            fig, ax = plt.subplots(figsize=(6, 6))

            

            wedges, texts, autotexts = ax.pie(

                koszty_wg_kategorii["Koszt"], 

                labels=koszty_wg_kategorii["Kategoria"], 

                autopct='%1.1f%%', 

                startangle=90,

                textprops={'color':"white", 'fontsize': 10}

            )

            

            plt.setp(autotexts, size=10, weight="bold", color="white")

            plt.setp(texts, size=10, color="white")



            ax.axis('equal')

            

            fig.patch.set_alpha(0)

            ax.patch.set_alpha(0)

            

            col_centered_pie = st.columns([1, 2, 1])

            with col_centered_pie[1]:

                 st.pyplot(fig, use_container_width=True)



        else:

            st.info("Dodaj koszty, aby zobaczyć wykresy.")

            

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

# ==========================

# ZAKŁADKA 4: STOŁY (NOWA)

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
            
            # Parsowanie listy gości
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
                    idx = int(df_stoly[df_stoly["Numer"] == wybrany_stol_id].index[0] + 2)
                    worksheet_stoly.update_cell(idx, 4, zapis_string)
                    st.cache_data.clear()
                    st.success("Zapisano gości!")
                    st.rerun()

            # --- WIZUALIZACJA (NOWE KOLORY I ROZMIARY) ---
            st.write("---")
            st.write(f"**Podgląd: {ksztalt_stolu} ({max_miejsc} os.)**")
            
            # ZWIĘKSZONA GRAFIKA
            fig, ax = plt.subplots(figsize=(10, 8)) # Większy rozmiar wykresu
            fig.patch.set_alpha(0)
            ax.patch.set_alpha(0)
            ax.set_aspect('equal')
            ax.axis('off')

            # --- DEFINICJA KOLORÓW ---
            table_color = '#a95e13'  # BRĄZOWY stół
            seat_color  = '#1B4D3E'  # Butelkowa zieleń
            text_color  = 'white'    # Biały tekst
            edge_color  = '#7B3F00'  # Ciemny brąz (obrys)

            if ksztalt_stolu == "Okrągły":
                # WIĘKSZY STÓŁ (promień 0.8)
                circle = plt.Circle((0, 0), 0.8, color=table_color, ec=edge_color, lw=2)
                ax.add_artist(circle)
                # Nazwa stołu na biało dla kontrastu
                ax.text(0, 0, wybrany_stol_id, ha='center', va='center', fontsize=12, fontweight='bold', color='white')

                for i in range(max_miejsc):
                    angle = 2 * np.pi * i / max_miejsc
                    # KRZESŁA DALEJ I WIĘKSZE
                    x = 1.1 * np.cos(angle) 
                    y = 1.1 * np.sin(angle)
                    
                    # Większe krzesło (promień 0.15)
                    seat = plt.Circle((x, y), 0.15, color=seat_color, alpha=1.0)
                    ax.add_artist(seat)
                    
                    guest_name = nowa_lista_gosci[i]
                    # Tekst jeszcze dalej
                    text_x = 1.4 * np.cos(angle)
                    text_y = 1.4 * np.sin(angle)
                    
                    rot = np.degrees(angle)
                    if 90 < rot < 270:
                        rot += 180
                        ha = 'right'
                    else:
                        ha = 'left'

                    # MNIEJSZA CZCIONKA NAZWISK (fontsize=8)
                    if guest_name:
                        ax.text(text_x, text_y, guest_name, ha=ha, va='center', rotation=rot, fontsize=8, color=text_color, fontweight='bold')
                    else:
                        ax.text(x, y, str(i+1), ha='center', va='center', fontsize=8, color='white')

                # Większy zakres osi
                ax.set_xlim(-2, 2)
                ax.set_ylim(-2, 2)

            elif ksztalt_stolu == "Prostokątny":
                # WIĘKSZY STÓŁ PROSTOKĄTNY (1.5x3)
                rect = plt.Rectangle((-0.75, -1.5), 1.5, 3, color=table_color, ec=edge_color, lw=2)
                ax.add_artist(rect)
                # Nazwa stołu na biało
                ax.text(0, 0, wybrany_stol_id, ha='center', va='center', rotation=90, fontsize=12, fontweight='bold', color='white')

                side_count = (max_miejsc + 1) // 2
                
                for i in range(max_miejsc):
                    guest_name = nowa_lista_gosci[i]
                    
                    # KRZESŁA BARDZIEJ ODSUNIĘTE (x=-1.3 i 1.3)
                    if i < side_count:
                        x = -1.5
                        # Rozłożenie wzdłuż dłuższego stołu
                        y = np.linspace(-1.2, 1.2, side_count)[i]
                        ha = 'right'
                    else:
                        x = 1.5
                        y = np.linspace(-1.2, 1.2, max_miejsc - side_count)[i - side_count]
                        ha = 'left'

                    # Większe krzesło i poprawiona pozycja kropki
                    seat = plt.Circle((x if x>0 else x, y), 0.15, color=seat_color, alpha=1.0)
                    if i < side_count: seat.center = (-1.15, y)
                    else: seat.center = (1.15, y)
                    ax.add_artist(seat)

                    if guest_name:
                        ax.text(x, y, guest_name, ha=ha, va='center', fontsize=8, color=text_color, fontweight='bold')
                    else:
                        seat_x, seat_y = seat.center
                        ax.text(seat_x, seat_y, str(i+1), ha='center', va='center', fontsize=8, color='white')

                # Większy zakres osi
                ax.set_xlim(-2.5, 2.5)
                ax.set_ylim(-2.5, 2.5)

            st.pyplot(fig, use_container_width=True)
            
            st.write("---")
            if st.button("🗑️ Usuń ten stół"):
                idx = int(df_stoly[df_stoly["Numer"] == wybrany_stol_id].index[0] + 2)
                worksheet_stoly.delete_rows(idx)
                st.cache_data.clear()
                st.warning("Usunięto stół!")
                st.rerun()
