import streamlit as st
import requests
import pandas as pd
from datetime import datetime, time

st.set_page_config(page_title="Tambah Data ke Sheet ALL", page_icon="📝", layout="wide")

APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbxXIGI_02cJUypyqfo2OvuzI2CR2vVkmJjlxa1yEFBLRDhFDFGbHNtxGyyL9M7k-MsSxQ/exec"

def get_spk_data():
    try:
        response = requests.get(APPS_SCRIPT_URL, params={"action": "get_spk"}, timeout=20)
        response.raise_for_status()
        return response.json().get("data", [])
    except requests.exceptions.RequestException as e:
        st.error(f"Terjadi kesalahan saat mengambil data SPK: {e}")
        return []

def get_database_sp():
    try:
        response = requests.get(APPS_SCRIPT_URL, params={"action": "get_DatabaseSP"}, timeout=20)
        response.raise_for_status()
        return response.json().get("data", [])
    except requests.exceptions.RequestException as e:
        st.error(f"Terjadi kesalahan saat mengambil Database SP: {e}")
        return []

def add_data_to_all(form_data):
    try:
        response = requests.post(APPS_SCRIPT_URL, json=form_data, timeout=20)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"status": "error", "error": str(e)}

def add_data_to_sparepart(form_data):
    try:
        response = requests.post(APPS_SCRIPT_URL, json=form_data, timeout=20)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"status": "error", "error": str(e)}

# mengambil data SPK dan data Sparepart
spk_data = get_spk_data()
database_sp = get_database_sp()

if isinstance(spk_data, list) and len(spk_data) > 0:
    df_spk = pd.DataFrame(spk_data)

    st.markdown("## Pilih ID SPK")
    id_options = df_spk["ID"].unique().tolist()
    selected_id = st.selectbox("Pilih ID SPK", id_options)

    selected_row = df_spk[df_spk["ID"] == selected_id].iloc[0]

    tanggal_pengerjaan = selected_row.get("Tanggal Pengerjaan", "").strip()
    if tanggal_pengerjaan:
        for fmt in ("%d-%b-%Y", "%d/%m/%Y", "%Y-%m-%d"):
            try:
                tanggal_pengerjaan = datetime.strptime(tanggal_pengerjaan, fmt).strftime("%Y-%m-%d")
                break
            except ValueError:
                continue
    else:
        tanggal_pengerjaan = "Tanggal tidak tersedia"

    st.markdown("### Data dari SPK")
    st.text(f"BU: {selected_row['BU']}")
    st.text(f"Line: {selected_row['Line']}")
    st.text(f"Produk: {selected_row['Produk']}")
    st.text(f"Mesin: {selected_row['Mesin']}")
    st.text(f"Masalah: {selected_row['Masalah']}")
    st.text(f"Tanggal: {tanggal_pengerjaan}")
    st.text(f"PIC: {selected_row['PIC']}")

    st.markdown("### Tambahkan Data ke Sheet ALL")
    mulai = st.time_input("Jam Mulai", value=time(0, 0))
    selesai = st.time_input("Jam Selesai", value=time(0, 0))
    tindakan = st.text_area("Tindakan Perbaikan")

    bu_filter = selected_row['BU']
    if isinstance(database_sp, list) and len(database_sp) > 0:
        df_database_sp = pd.DataFrame(database_sp)

        if "BU" in df_database_sp.columns and "Deskripsi" in df_database_sp.columns and "UOM" in df_database_sp.columns:
            filtered_db = df_database_sp[df_database_sp['BU'] == bu_filter]
            unique_descriptions = filtered_db[['Deskripsi', 'UOM']].drop_duplicates()['Deskripsi'].tolist()
        else:
            st.error("Kolom 'BU', 'Deskripsi', atau 'UOM' tidak ditemukan dalam database SP!")
            unique_descriptions = []
    else:
        st.warning("Database Sparepart kosong!")
        unique_descriptions = []

    selected_items = st.multiselect("Pilih Deskripsi Sparepart", unique_descriptions)

    if selected_items:
        data = {'Item': selected_items, 'Quantity': [0] * len(selected_items)}
        df = pd.DataFrame(data)

        # table editor untuk memasukkan kuantitas
        edited_df = st.data_editor(df, key="data_editor")

        # isi setelah pengguna mengedit
        st.write("Hasil:")
        st.dataframe(edited_df)

    else:
        st.write("Silakan pilih deskripsi untuk melanjutkan.")

    submitted = st.button("Tambah Data")

    if submitted:
        if selesai <= mulai:
            st.error("Waktu selesai harus lebih besar dari waktu mulai.")
        else:
            mulai_str = mulai.strftime("%H:%M")
            selesai_str = selesai.strftime("%H:%M")

            if selected_items:
                quantities = edited_df['Quantity'].tolist()
            else:
                quantities = []

            if len(selected_items) == len(quantities):
                data_to_send = {
                    "action": "add_data",
                    "ID_SPK": selected_id,
                    "BU": selected_row['BU'],
                    "Line": selected_row['Line'],
                    "Produk": selected_row['Produk'],
                    "Mesin": selected_row['Mesin'],
                    "Tanggal": tanggal_pengerjaan,
                    "Mulai": mulai_str,
                    "Selesai": selesai_str,
                    "Masalah": selected_row['Masalah'],
                    "Tindakan": tindakan,
                    "Deskripsi": ", ".join(selected_items),  
                    "Quantity": ", ".join(map(str, quantities)),  
                    "PIC": selected_row['PIC']
                }

                response = add_data_to_all(data_to_send)

                if response.get("status") == "success":
                    st.success("Data berhasil ditambahkan ke Sheet ALL! ✅")
                    st.rerun()
                else:
                    st.error(f"Gagal menambahkan data: {response.get('error', 'Tidak diketahui')}")

                # format data Sparepart untuk dipisah per baris di sheet SPAREPART
                sparepart_data_list = []
                for item, qty in zip(selected_items, quantities):
                    uom_value = filtered_db.loc[filtered_db['Deskripsi'] == item, 'UOM'].values
                    uom_final = uom_value[0] if len(uom_value) > 0 else "UNKNOWN"

                    sparepart_data_list.append({
                        "action": "add_data_to_sparepart",
                        "ID_SPK": selected_id,
                        "Deskripsi": item,
                        "Quantity": qty,
                        "UOM": uom_final
                    })

                # setiap data sparepart sebagai baris terpisah
                for sparepart_data in sparepart_data_list:
                    sparepart_response = add_data_to_sparepart(sparepart_data)
                    
                    if sparepart_response.get("status") == "success":
                        st.success(f"Data sparepart '{sparepart_data['Deskripsi']}' berhasil ditambahkan! ✅")
                    else:
                        st.error(f"Gagal menambahkan '{sparepart_data['Deskripsi']}': {sparepart_response.get('error', 'Tidak diketahui')}")
            else:
                st.error("Jumlah deskripsi dan kuantitas tidak sesuai!")
else:
    st.warning("⚠ Tidak ada data SPK yang tersedia.")

