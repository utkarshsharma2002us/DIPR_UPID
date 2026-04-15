import os
import json
import pdfplumber
import re
import pandas as pd
from rapidfuzz import process, fuzz
import package_mapping

# ---------------- CONFIG ----------------
INPUT_FOLDER = "input_dipr"
OUTPUT_JSON = "output.json"
OUTPUT_CSV = "output_dipr.csv"
ERROR_CSV = "error.csv"

# ---------------- REQUIRED FIELDS ----------------
required_fields = [
    "FILE_NAME", "AGENCY_NAME", "AGENCY_CODE", "Agency_code_subcode",
    "CLIENT_CODE", "RO_CLIENT_NAME", "RO_CLIENT_CODE", "RO_NUMBER",
    "RO_DATE", "GSTIN", "CATEGORY", "COLOUR", "PACKAGE_NAME",
    "INSERT_DATE", "RO_REMARKS", "Newspaper Name", "BRAND", "AD_CAT","AD_SUBCAT", "AD_HEIGHT",
    "AD_WIDTH", "AD_SIZE", "PAGE_PREMIUM", "POSITIONING",
    "RO_RATE", "RO_AMOUNT", "AD_DISCOUNT"
]

# ---------------- CLEANING FUNCTION ----------------
def clean_name(name):
    if pd.isna(name):
        return ""
    name = name.lower().strip()
    name = re.sub(r"[-\.\'\[\]\(\)]", "", name)
    name = re.sub(r"\s+", " ", name)
    return name

# ---------------- LOAD MASTER DATA ONCE ----------------
df_master = pd.read_csv("DIPR_filtered_df.csv")
df_master["MASTER_CLIENT_NAME_CLEAN"] = df_master["MASTER_CLIENT_NAME"].apply(clean_name)

# ---------------- TEXT EXTRACTION ----------------
def extract_text_from_pdf(pdf_path):
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
    except Exception as e:
        print(f"Error reading PDF {pdf_path}: {e}")
    return text

# ---------------- CLIENT MATCHING ----------------
def get_client_code(ro_client_name_combined):

    Ro_client_name_clean = clean_name(ro_client_name_combined)

    # Exact match
    match = df_master[
        (df_master["MASTER_CLIENT_NAME_CLEAN"] == Ro_client_name_clean)
    ]

    # Fuzzy match
    if match.empty:
        choices = df_master["MASTER_CLIENT_NAME_CLEAN"].tolist()

        best_match = process.extractOne(
            Ro_client_name_clean,
            choices,
            scorer=fuzz.token_sort_ratio
        )

        if best_match:
            matched_name, score, idx = best_match
            if score >= 80:  # Threshold for good match
                return df_master.iloc[idx]["MASTER_CLIENT_CODE"]
        return "-"
    return match.iloc[0]["MASTER_CLIENT_CODE"]



# ---------------- MAIN EXTRACTION ----------------
def extract_invoice_data(text, file_name):

    data = {field: "" for field in required_fields}

    # Defaults
    data["RO_CLIENT_CODE"] = "-"
    data["POSITIONING"] = "-"

    # -------- Basic Fields --------
    agency_code = re.search(r'PRDH:-([\d/]+)', text)
    ro_no = re.search(r'RO No:-([\d/]+)', text)
    ro_date = re.search(r'Dated .*?(\d{2}/\d{2}/\d{4})', text)
    gstin = re.search(r'GSTIN\s*-\s*(\w+)', text)

    remarks = re.search(r'5\.\s+Remarks\s+(.*?)\n', text)
    discount_match = re.search(r'(\d+(?:\.\d+)?)%\s*.*Media', text, re.IGNORECASE)
    

    data["FILE_NAME"] = file_name
    data["AGENCY_NAME"] = "DIPR Haryana"
    data["BRAND"] = "NONE"
    data["AD_CAT"] = "GO2"
    data["AGENCY_CODE"] = "None"
    data["Agency_code_subcode"] = "DI11DIP1"
    data["RO_NUMBER"] = ro_no.group(1) if ro_no else ""
    data["RO_DATE"] = ro_date.group(1) if ro_date else ""
    data["GSTIN"] = gstin.group(1) if gstin else ""
    

    # -------- PACKAGE --------
    edition_matches = re.findall(r'Amar Ujala,\s*([A-Za-z ]+)CLASSIFIED', text, re.IGNORECASE)
    if edition_matches:
        editions_clean = [e.strip().upper() for e in edition_matches]
        data["PACKAGE_NAME"] = ", ".join(editions_clean)
        
    if editions_clean:
        packages = []
        for edition in editions_clean:
            mapped_package = package_mapping.PACKAGE_NAME_MAP.get(edition, edition)
            packages.append(mapped_package)
        data["PACKAGE_NAME"] = ", ".join(packages)
    else:
        data["PACKAGE_NAME"] = ""

    # -------- CLIENT NAME EXTRACTION --------    
    client_match_ad = re.search(r'Dept\.?\s*to\s*which\s*advt\.?\s*relates\s*(.*?)\s*(?:\n|Office|Managing|Director|Under)',text,re.IGNORECASE | re.DOTALL)
    if client_match_ad:
        client_match_advt = client_match_ad.group(1).replace("\n", " ").strip()
    client_match = re.search(r'Office/\s*Authorized\s*Officer\s*of\s*client\s*department\s*(.*?)(?:\n\s*\n|\n\d+\.|\Z)',text,re.IGNORECASE | re.DOTALL)

    if client_match:
        full_text = client_match.group(1)

        full_text = re.sub(r'which\s*advt\.?\s*relates', '', full_text, flags=re.IGNORECASE)
        full_text = full_text.replace("\n", " ").strip()

        parts = [p.strip() for p in full_text.split(",") if p.strip()]

        if parts:
            client_name = parts[0]
            city_name = parts[-1].rstrip(".")

            Ro_client_name_combined = client_name + " " + city_name
            data["RO_CLIENT_NAME"] = client_match_advt + ", " + Ro_client_name_combined

            # 🔥 MATCHING
            data["CLIENT_CODE"] = get_client_code(Ro_client_name_combined)

    # -------- REMARKS --------
    data["RO_REMARKS"] = remarks.group(1).strip() if remarks else ""
    data["AD_DISCOUNT"] = float(discount_match.group(1)) if discount_match else 0.0

    # -------- INSERT DATE --------
    pub_date_match = re.search(r'Publication\s*Date.*?(\d{2}-\d{2}-\d{4})',text,re.IGNORECASE | re.DOTALL)
    if pub_date_match:
        data["INSERT_DATE"] = pub_date_match.group(1)

    # -------- NEWSPAPER --------
    paper_match = re.search(r'Amar Ujala,\s*([A-Za-z ]+) Classified', text)
    if paper_match:
        data["Newspaper Name"] = f"Amar Ujala {paper_match.group(1).strip()}"

    # -------- SIZE --------
    size_match = re.search(r'/\s*([\d.]+)\s*\(Sq', text)
    if size_match:
        size = float(size_match.group(1))
        data["AD_SIZE"] = size
        data["AD_HEIGHT"] = 1
        data["AD_WIDTH"] = size

    subject_match = re.search(r'Subject matter of the advertisement\s*([^\n\r]+)',text,re.IGNORECASE)
    if subject_match:
        data["CATEGORY"] = subject_match.group(1).strip()

# -------- AD CATEGORY --------

    if data["CATEGORY"] == "Tender" or data["CATEGORY"] == "Auction":
        data["AD_SUBCAT"] = "GO5"
    else:
        data["AD_SUBCAT"] = "GO8"

    # -------- COLOUR --------
    color_match = re.search(r'(B&W|Colored)', text, re.IGNORECASE)
    if color_match:
        data["COLOUR"] = "B" if "B" in color_match.group(1).upper() else "C"

    # -------- POSITION --------
    if "Any Page" in text:
        data["POSITIONING"] = "Any Page"
        data["PAGE_PREMIUM"] = "YES"
    else:
        data["PAGE_PREMIUM"] = "NO"

    # -------- RATE --------
    rate_matches = re.findall(r'Rs\.(\d+\.\d+)', text)
    rates = [float(r) for r in rate_matches]
    data["RO_RATE"] = sum(rates) if rates else 0.0

    # -------- AMOUNT --------
    amount_match = re.search(r'Total Cost:\s*Rs\.?\s*([\d,]+\.\d+)', text)
    if amount_match:
        data["RO_AMOUNT"] = float(amount_match.group(1).replace(",", ""))

    return data

# ---------------- PROCESS FOLDER ----------------
def process_folder(folder_path):

    all_data = []
    valid_data = []
    error_records = []

    for file in os.listdir(folder_path):
        if file.lower().endswith(".pdf"):

            pdf_path = os.path.join(folder_path, file)
            print(f"Processing: {file}")

            try:
                text = extract_text_from_pdf(pdf_path)
                data = extract_invoice_data(text, file)

                all_data.append(data)

                missing_fields = [
                    field for field in required_fields
                    if not data.get(field)
                ]

                if missing_fields:
                    error_records.append({
                        "PDF File": file,
                        "Missing Fields": ", ".join(missing_fields)
                    })
                else:
                    valid_data.append(data)

            except Exception as e:
                print(f"Error in {file}: {e}")
                error_records.append({
                    "PDF File": file,
                    "Error": str(e)
                })

    # Save JSON
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=4)

    # Save CSV
    if valid_data:
        df = pd.DataFrame(valid_data)
        df = df.reindex(columns=required_fields)
        df.to_csv(OUTPUT_CSV, index=False)

    # Save Errors
    if error_records:
        pd.DataFrame(error_records).to_csv(ERROR_CSV, index=False)

    print("\nProcessing Completed")
    print(f"Total Records: {len(all_data)}")
    print(f"Valid Records: {len(valid_data)}")
    print(f"Errors: {len(error_records)}")

# ---------------- RUN ----------------
if __name__ == "__main__":
    process_folder(INPUT_FOLDER)
