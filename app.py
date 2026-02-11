import streamlit as st

import pandas as pd

import gspread

from oauth2client.service_account import ServiceAccountCredentials

from datetime import date

import matplotlib.pyplot as plt

import altair as alt

import numpy as np

# --- STYLIZACJA CSS (UI) ---
# --- STYLIZACJA CSS (UI) ---
def local_css():
    st.markdown("""
    <style>
        /* Zmiana fontu dla całej strony */
        html, body, [class*="css"] {
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        }
        
        /* PRZESUNIĘCIE TYTUŁU JESZCZE WYŻEJ */
        .block-container {
            padding-top: 1rem !important; /* Było 2rem, teraz 1rem - tytuł pójdzie w górę */
            padding-bottom: 2rem !important;
        }
        
        /* Ukrycie menu hamburgera i stopki */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        
        /* Stylizacja nagłówków */
        h1 {
            color: #8B4513; /* Brązowy */
            text-align: center;
            font-weight: 1000;
            margin-bottom: 0px;
        }
        h2 {
            color: #1B4D3E; /* Butelkowa zieleń */
            border-bottom: 2px solid #FFFFFF;
            padding-bottom: 10px;
        }
        
        /* --- UJEDNOLICENIE KOLORÓW --- */
        
        /* 1. Kafelki (Metryki) - Tło ciemnoszare (zamiast czarnego) */
        [data-testid="stMetric"] {
            background-color: #262730 !important; /* Standardowy ciemny kolor kart Streamlit */
            border: 1px solid #444; /* Delikatna ramka */
            padding: 15px;
            border-radius: 10px;
            box-shadow: 2px 2px 10px rgba(0,0,0,0.5);
        }
        
        /* 2. Tabele - Ramka w tym samym kolorze co tło kafelków (opcjonalnie tło też) */
        [data-testid="stDataEditor"] {
            border: 1px solid #444 !important; /* Ramka pasująca do kafelków */
            border-radius: 10px;
            background-color: #262730; /* Tło pod tabelą identyczne jak kafelki */
        }
        
        /* Kolory tekstów w kafelkach */
        [data-testid="stMetricLabel"] {
            color: white !important; /* Beżowy */
        }
        [data-testid="stMetricValue"] {
            color: #4CAF50 !important; /* Zielony */
        }

        div[data-baseweb="tab-panel"]:nth-of-type(2) div[data-testid="column"]:nth-of-type(3) [data-testid="stMetricValue"] {
            color: #ff4b4b !important; /* Czerwony */
        }
        
        /* Powiększenie zakładek (Tabs) */
        button[data-baseweb="tab"] {
            font-size: 18px !important;
            font-weight: 600 !important;
        }
        
        /* Kolor aktywnej zakładki */
        button[data-baseweb="tab"][aria-selected="true"] {
            color: white !important;
        }
    </style>
    """, unsafe_allow_html=True)

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Menadżer Ślubny", page_icon="💍", layout="wide")

# --- WYWOŁANIE STYLI ---
local_css()

# --- STAŁE ---
LISTA_KATEGORII_BAZA = [

    "Inne"

]

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

    st.header("👥 Zarządzanie Gośćmi")

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
    
    df_obsluga.columns = df_obsluga.columns.str.strip()
    for c in org_cols:
        if c not in df_obsluga.columns:
            df_obsluga[c] = ""
            if c == "Kategoria": df_obsluga[c] = "Inne"

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

    # --- NOWY UKŁAD FORMULARZA ---
    with st.expander("➕ Dodaj koszt", expanded=False):
        # 1. Kategoria i Nowa Nazwa
        c_select, c_input = st.columns(2)
        with c_select:
            sel = st.selectbox("Kategoria", select_opts, key="org_k_sel")
        with c_input:
            if sel == "➕ Stwórz nową...": st.text_input("Nowa nazwa:", key="org_k_inp")
        
        # 2. Rola
        st.text_input("Rola", key="org_rola", placeholder="np. DJ, Florystka")
        
        # 3. Finanse OBOK SIEBIE (Koszt i Zaliczka)
        c1, c2 = st.columns(2)
        with c1:
            st.number_input("Koszt Całkowity (zł)", step=100.0, key="org_koszt")
            st.checkbox("Całość opłacona?", key="org_op")
        with c2:
            st.number_input("Zaliczka (zł)", step=100.0, key="org_zal")
            st.checkbox("Zaliczka opłacona?", key="org_z_op")
            
        # 4. Info NA DOLE (Szerokie)
        st.text_input("Informacje dodatkowe", key="org_info", placeholder="Kontakt, termin płatności...")
        
        st.button("Dodaj", on_click=dodaj_usluge, key="btn_org")

    st.write("---")
    st.subheader(f"💸 Wydatki ({len(df_obsluga)})")
    
    fil = st.multiselect("🔍 Filtruj:", all_cats)
    df_disp = df_obsluga.copy()
    if fil: df_disp = df_disp[df_disp["Kategoria"].isin(fil)]

    # Konwersja typów
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

    # --- NOWOŚĆ: DYNAMICZNY MAX DLA PASKA POSTĘPU ---
    # Obliczamy sumę wszystkich kosztów w tabeli i ustawiamy ją jako 100% paska
    max_budget_value = int(df_disp["Koszt"].sum())
    if max_budget_value == 0: max_budget_value = 100 # Zabezpieczenie przed 0

    edited_org = st.data_editor(
        df_disp, num_rows="dynamic", use_container_width=True, hide_index=True, key="ed_org",
        column_config={
            "Kategoria": st.column_config.SelectboxColumn("Kategoria", options=all_cats, required=True),
            "Rola": st.column_config.TextColumn("Rola", required=True),
            "Informacje": st.column_config.TextColumn("Info", width="large"),
            # Pasek postępu z dynamicznym max_value
            "Koszt": st.column_config.ProgressColumn(
                "Koszt", 
                format="%d zł", 
                min_value=0, 
                max_value=max_budget_value 
            ),
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
        c3.metric("Do zapłaty", f"{total-paid:,.0f} zł", delta=-(total-paid), delta_color="red")

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
            ).properties(height=300).interactive()
            st.altair_chart(chart, use_container_width=True)

            st.write("---")
            st.write("**Udział procentowy**")
            
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

    try:
        df_stoly = pobierz_dane(worksheet_stoly)
    except Exception as e:
        st.error("Problem z zakładką 'Stoly'. Sprawdź czy istnieje.")
        st.stop()

    cols_stoly = ["Numer", "Ksztalt", "Liczba_Miejsc", "Goscie_Lista"]
    if df_stoly.empty:
        df_stoly = pd.DataFrame(columns=cols_stoly)
    
    if not df_stoly.empty:
        df_stoly.columns = df_stoly.columns.str.strip()
    for c in cols_stoly:
        if c not in df_stoly.columns: df_stoly[c] = ""

    if not df_stoly.empty:
        df_stoly["Numer"] = df_stoly["Numer"].astype(str)
        df_stoly["Liczba_Miejsc"] = pd.to_numeric(df_stoly["Liczba_Miejsc"], errors='coerce').fillna(0).astype(int)

    col_left, col_right = st.columns([1, 2])

    with col_left:
        st.subheader("➕ Dodaj Stół")
        with st.form("dodaj_stol_form"):
            nr_stolu = st.text_input("Numer/Nazwa Stołu", placeholder="np. Stół 1 lub Wiejski")
            ksztalt = st.selectbox("Kształt", ["Okrągły", "Prostokątny"])
            miejsca = st.number_input("Liczba Miejsc", min_value=1, max_value=24, value=8)
            submitted = st.form_submit_button("Dodaj Stół")
            
            if submitted and nr_stolu:
                pusta_lista = ";".join(["" for _ in range(miejsca)])
                zapisz_nowy_wiersz(worksheet_stoly, [nr_stolu, ksztalt, miejsca, pusta_lista])
                st.toast(f"Dodano stół: {nr_stolu}")
                st.rerun()

        st.write("---")
        st.subheader("📋 Lista Stołów")
        
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
            
            # Pobieramy dane
            row = df_stoly[df_stoly["Numer"] == wybrany_stol_id].iloc[0]
            max_miejsc = int(row["Liczba_Miejsc"])
            ksztalt_stolu = row["Ksztalt"]
            
            obecni_goscie_str = str(row["Goscie_Lista"])
            if ";" in obecni_goscie_str:
                lista_gosci = obecni_goscie_str.split(";")
            else:
                lista_gosci = [""] * max_miejsc
            
            if len(lista_gosci) < max_miejsc:
                lista_gosci += [""] * (max_miejsc - len(lista_gosci))
            lista_gosci = lista_gosci[:max_miejsc]

            # --- FORMULARZ ---
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
                    st.success("Zapisano!")
                    st.rerun()

            # --- WIZUALIZACJA ---
            st.write("---")
            st.write(f"**Podgląd: {ksztalt_stolu} ({max_miejsc} os.)**")
            
            # --- ZMIANA TUTAJ: ZWIĘKSZONY ROZMIAR GRAFIKI (20x16 cali) ---
            fig, ax = plt.subplots(figsize=(20, 16))
            fig.patch.set_alpha(0)
            ax.patch.set_alpha(0)
            ax.set_aspect('equal')
            ax.axis('off')

            # --- KOLORY ---
            table_color = '#9D5B03'  # Brązowy
            seat_color  = '#1B4D3E'  # Butelkowa zieleń
            text_color  = 'white'
            edge_color  = '#7B3F00'  # Ciemny obrys

            if ksztalt_stolu == "Okrągły":
                # Promienie
                R_STOL = 1.1
                R_KRZESLO_SRODEK = 1.4
                R_TEKST = 1.65

                # Stół
                circle = plt.Circle((0, 0), R_STOL, color=table_color, ec=edge_color, lw=4)
                ax.add_artist(circle)
                # Większa czcionka nazwy stołu (24)
                ax.text(0, 0, wybrany_stol_id, ha='center', va='center', fontsize=24, fontweight='bold', color='white')

                for i in range(max_miejsc):
                    angle = 2 * np.pi * i / max_miejsc
                    
                    # Pozycja krzesła
                    cx = R_KRZESLO_SRODEK * np.cos(angle)
                    cy = R_KRZESLO_SRODEK * np.sin(angle)
                    
                    # Rysujemy krzesło
                    seat = plt.Circle((cx, cy), 0.21, color=seat_color, alpha=1.0)
                    ax.add_artist(seat)
                    
                    guest_name = nowa_lista_gosci[i]
                    
                    # Pozycja tekstu
                    tx = R_TEKST * np.cos(angle)
                    ty = R_TEKST * np.sin(angle)
                    
                    rot_deg = np.degrees(angle)
                    
                    if 90 < rot_deg < 270:
                        rot_deg += 180
                        ha = 'right'
                    else:
                        ha = 'left'

                    if guest_name:
                        # Większa czcionka nazwisk (16)
                        ax.text(tx, ty, guest_name, ha=ha, va='center', 
                                rotation=rot_deg, rotation_mode='anchor', 
                                fontsize=16, color=text_color, fontweight='bold')
                    else:
                        # Większa czcionka numerów (14)
                        ax.text(cx, cy, str(i+1), ha='center', va='center', fontsize=16, color='white')

                limit = 2.2
                ax.set_xlim(-limit, limit)
                ax.set_ylim(-limit, limit)

            elif ksztalt_stolu == "Prostokątny":
                # Wymiary
                W_STOL = 2.0
                H_STOL = 4.0
                
                rect = plt.Rectangle((-W_STOL/2, -H_STOL/2), W_STOL, H_STOL, color=table_color, ec=edge_color, lw=4)
                ax.add_artist(rect)
                # Większa czcionka nazwy stołu (24)
                ax.text(0, 0, wybrany_stol_id, ha='center', va='center', rotation=90, fontsize=24, fontweight='bold', color='white')

                side_count = (max_miejsc + 1) // 2
                
                DIST_X = 1.3
                
                for i in range(max_miejsc):
                    guest_name = nowa_lista_gosci[i]
                    
                    if i < side_count:
                        # LEWA
                        x_pos = -DIST_X
                        y_pos = np.linspace(-H_STOL/2 + 0.4, H_STOL/2 - 0.4, side_count)[i]
                        ha = 'right'
                        text_offset_x = -0.25
                    else:
                        # PRAWA
                        x_pos = DIST_X
                        y_pos = np.linspace(-H_STOL/2 + 0.4, H_STOL/2 - 0.4, max_miejsc - side_count)[i - side_count]
                        ha = 'left'
                        text_offset_x = 0.25

                    # Krzesło
                    seat = plt.Circle((x_pos, y_pos), 0.21, color=seat_color, alpha=1.0)
                    ax.add_artist(seat)

                    if guest_name:
                        # Większa czcionka nazwisk (16)
                        ax.text(x_pos + text_offset_x, y_pos, guest_name, ha=ha, va='center', 
                                fontsize=16, color=text_color, fontweight='bold')
                    else:
                        # Większa czcionka numerów (14)
                        ax.text(x_pos, y_pos, str(i+1), ha='center', va='center', fontsize=16, color='white')

                ax.set_xlim(-2.8, 2.8)
                ax.set_ylim(-2.8, 2.8)

            st.pyplot(fig, use_container_width=True)
            
            st.write("---")
            if st.button("🗑️ Usuń ten stół"):
                idx = int(df_stoly[df_stoly["Numer"] == wybrany_stol_id].index[0] + 2)
                worksheet_stoly.delete_rows(idx)
                st.cache_data.clear()
                st.warning("Usunięto stół!")
                st.rerun()
