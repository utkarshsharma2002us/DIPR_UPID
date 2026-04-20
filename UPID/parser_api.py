import base64
import csv
import json
import io
import os
import re
from dotenv import load_dotenv
from openai import OpenAI

# Load API key
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY not found in .env file")

client = OpenAI(api_key=api_key)

def encode_image(file_path):
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def format_date(date_str):
    if not date_str:
        return ""
    match = re.search(r'(\d{2})[/-](\d{2})[/-](\d{4})', date_str)
    if match:
        return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
    return ""


def process_input_folder(input_folder, output_file):

    headers = [
        "FILE_NAME", "GSTIN","CLIENT_CODE", "CLIENT_NAME","CITY_NAME",
        "RO_CLIENT_CODE", "RO_CLIENT_NAME","AGENCY_NAME", "AGENCY_CODE", "AGENCY_CODE_SUBCODE",
        "AD_CAT", "AD_HEIGHT", "AD_WIDTH",
        "RO_NUMBER", "RO_DATE", "KEY_NUMBER", "CATEGORY", "COLOUR",
        "AD_SUBCAT", "PRODUCT", "BRAND", "PACKAGE_NAME",
        "INSERT_DATE", "RO_REMARKS",
        "AD_SIZE", "Executive", "PAGE_PREMIUM", "POSITIONING",
        "RO_RATE", "RO_AMOUNT", "EXTRACTED_TEXT"
    ]
    
    Fixed_values = {
        "AGENCY_NAME": "सूचना एवं जनसंपर्क विभाग",
        "AGENCY_CODE": "U.56U.P55",
        "AGENCY_CODE_SUBCODE": "NONE",
        "AD_CAT": "G02",
        "AD_HEIGHT": "1",
        "AD_WIDTH": "1",
        "CATEGORY": "Display",
        "AD_SUBCAT": "GOVT. DISPLAY",
        "PRODUCT": "DISPLAY ADVERTISING",
    }
    
    Package_mapping = {
        "DEHRADUN": "AU-DDN",
        "AGRA": "AU-AGR",
        "DELHI": "AU-NWD",
        "CHANDIGARH": "AU-CHD",
        "ROHTAK": "AU-RTK",
        "NAINITAL": "AU-NTL",
        "LUCKNOW": "AU-LKO",
        "PRAYAGRAJ": "AU-ALD",
        "JHANSI": "AU-JHA",
        "VARANASI": "AU-VNS",
        "JALANDHAR": "AU-JAL",
        "DHARAMSHALA": "AU-DHM",
        "ALIGARH": "AU-ALG",
        "GORAKHPUR": "AU-GKP",
        "BAREILLY": "AU-BLY",
        "MEERUT": "AU-MRT",
        "MORADABAD": "AU-MBD",
        "KANPUR": "AU-KNP",
        "SHIMLA": "AU-SML",
        "HISAR": "AU-HIS",
        "KARNAL": "AU-KNL",
        "JAMMU": "AU-JMU"
        }

    results = []

    for file_name in os.listdir(input_folder):
        file_path = os.path.join(input_folder, file_name)

        if not file_name.lower().endswith((".pdf", ".jpg", ".jpeg", ".png")):
            continue

        print(f"Processing: {file_name}")

        try:
            prompt = f"""
            You are an expert data extraction engine specialized in Indian Government Release Orders (ROs), including Hindi and English documents.
            Your task is to extract structured data from a Release Order (RO) document and return a STRICT JSON output.

Your task is also to clean garbled Unicode text extracted from PDFs.(
Rules:
1. Fix broken or corrupted Unicode characters.
2. Restore readable Hindi (Devanagari) text wherever possible.
3. Do NOT translate the text.
4. Do NOT summarize or change meaning.
5. Preserve original structure, numbering, and formatting.
6. If a word is too corrupted to fix, leave it as-is instead of guessing.
7. Remove random symbols, junk characters, and encoding artifacts.
)
----------------------------------------
🧠 CORE CAPABILITIES REQUIRED
----------------------------------------
1. Understand both Hindi and English text.
2. Translate Hindi content into English internally before mapping.
3. Identify structured tabular and unstructured data.
4. Apply strict business rules (NO GUESSING).
5. Filter and extract ONLY "AMAR UJALA" newspaper data if multiple newspapers are present.
----------------------------------------
⚠️ CRITICAL FILTER RULE
----------------------------------------
- If multiple newspapers exist → ONLY extract row where newspaper name is:
  "AMAR UJALA" (or Hindi: "अमर उजाला")
- Ignore all other newspapers completely.
- Ignore/ Skip all data of section महोदय,
----------------------------------------
📦 OUTPUT FORMAT (STRICT JSON ONLY)
----------------------------------------
Return ONLY valid JSON with the following fields:
Keys: {', '.join(headers)}
----------------------------------------
📘 FIELD EXTRACTION RULES
----------------------------------------
🔹 RO_NUMBER
- Extract from: "आo ओo संख्या", "RO No", "R.O."
- Numeric value only
🔹 RO_DATE
- Extract from: "दिनांक"
- Format strictly: dd-mm-yyyy
🔹 INSERT_DATE
- Extract publication date or range
- Convert to: dd-mm-yyyy
- If range → take the first date only
🔹 CITY_NAME
- Extract from agency address/location
- Usually appears in header (e.g., Lucknow)
🔹 RO_CLIENT_NAME
- Extract after "प्रतिलिपि:" and before ", को उनके पत्र संख्या" 
🔹 CATEGORY
- Detect based on content:
    Government ads → "Display"
    Tender-related → "Tender"
    Recruitment → "Recruitment"
🔹 PRODUCT (choose ONE only)
- DISPLAY ADVERTISING
- TENDER
- PUBLIC NOTICES
- AUCTION
- RECRUITMENT
- ADMISSION NOTICE
- ANNOUNCEMENTS
- OTHERS
🔹 AD_SUBCAT (based on CATEGORY)
- Display → GOVT. DISPLAY
- Tender → GOVT.TENDER
- Others → GOVT. DISPLAY
🔹 AD_SIZE
- Extract numeric ad size (sq cm) from Amar Ujala row from आवृत स्थान वर्ग सेमी. मी0
- DO NOT calculate
🔹 COLOUR
- Only if explicitly mentioned:
  "C" or "B"
- Else → ""
🔹 RO_RATE
- Extract rate from Amar Ujala row from दर वर्ग सेमीमी0 
🔹 RO_AMOUNT
- Extract ONLY Amar Ujala amount
- DO NOT take total of all newspapers
🔹 PACKAGE_NAME (VERY IMPORTANT)
- Extract city/edition name from Amar Ujala row only (Strictly from Amar Ujala row only)
- Convert to CITY CODE using mapping from: {json.dumps(Package_mapping, indent=4)}
- If not found → ""
🔹 RO_REMARKS
- Extract:
  - Publication date range OR
  - Any remarks related to advertisement
🔹 KEY_NUMBER
- Extract from "को उनके पत्र संख्या"
  
Hardcoded values:
{json.dumps(Fixed_values, indent=4)}
----------------------------------------
🚫 STRICT RULES (VERY IMPORTANT)
----------------------------------------
- DO NOT GUESS any value
- If value not found → return ""
- DO NOT calculate missing values
- DO NOT include other newspapers
- DO NOT hallucinate GSTIN, amounts, or rates
- Always return clean English output (no Hindi in final JSON)
----------------------------------------
📄 EXTRACTED_TEXT
----------------------------------------
- Include FULL RAW OCR TEXT exactly as input (after cleaning garbled Unicode)
----------------------------------------
🧪 FINAL VALIDATION BEFORE OUTPUT
----------------------------------------
- Ensure only Amar Ujala data is used
- Ensure JSON is valid
- Ensure all dates are dd-mm-yyyy
- Ensure no extra fields
- Ensure empty fields are ""
----------------------------------------
OUTPUT ONLY JSON. NO EXPLANATION.
----------------------------------------
"""
            # -------- PDF --------
            if file_name.lower().endswith(".pdf"):
                uploaded = client.files.create(
                    file=open(file_path, "rb"),
                    purpose="assistants"
                )

                response = client.responses.create(
                    model="gpt-4.1-mini",
                    input=[{
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": prompt},
                            {"type": "input_file", "file_id": uploaded.id}
                        ]
                    }]
                )

                raw = response.output_text.strip()

            # -------- IMAGE --------
            else:
                base64_data = encode_image(file_path)

                response = client.chat.completions.create(
                    model="gpt-4.1-mini",
                    temperature=0,
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_data}"
                                }
                            }
                        ]
                    }]
                )

                raw = response.choices[0].message.content.strip()

            # CLEAN JSON TEXT
            raw = raw.replace("\n", "").replace("\r", "").strip()

            def extract_json(text):
                if not text:
                    return "{}"
                match = re.search(r"\{.*\}", text, re.DOTALL)
                if match:
                    return match.group(0)
                return "{}"

            clean_json = extract_json(raw)
            try:
                data = json.loads(clean_json)
            except:
                data = {}

            # Ensure all keys exist
            for key in headers:
                data.setdefault(key, "")

            # FILE_NAME
            data["FILE_NAME"] = file_name

            # CLEAN RO_NUMBER
            data["RO_NUMBER"] = re.sub(r"\s+", "", data.get("RO_NUMBER", ""))

            # FORMAT DATES
            data["RO_DATE"] = format_date(data.get("RO_DATE", ""))
            data["INSERT_DATE"] = format_date(data.get("INSERT_DATE", ""))

            # PACKAGE_NAME uppercase
            data["PACKAGE_NAME"] = data.get("PACKAGE_NAME", "").upper().strip()

            # PAGE_PREMIUM logic
            pos = data.get("POSITIONING", "").strip()
            data["PAGE_PREMIUM"] = "YES" if pos else "NO"

            results.append(data)

        except Exception as e:
            print(f"❌ Error in {file_name}: {e}")
    
        # SAVE JSON
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)

    print("✅ JSON saved.")

    # SAVE CSV
    csv_file = output_file.replace(".json", ".csv")

    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)

        writer.writeheader()
        writer.writerows(results)

    print("✅ CSV saved.")


# RUN
if __name__ == "__main__":
    process_input_folder(r"Upid_input", r"output.json") # input_folder_contains_pdf, output_json_file
