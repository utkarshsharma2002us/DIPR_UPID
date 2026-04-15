import logging
import os
import shutil
import pdfplumber
import re

SAMVAD_KEYWORDS = [
    "SOCIETY FOR ADVANCED MANAGEMENT OF COMMUNICATION",
    "SAMVAD",
    "MD -CUM- CEO",
    "VALUE ADDED DISSEMINATION OF INFORMATION ADVERTISEMENT RELEASE"
]

CBC_KEYWORDS = [
    "CENTRAL BUREAU OF COMMUNICATION",
    "GOVERNMENT OF INDIA",
    "RO CODE",
    "CBC"
]

DIPR_KEYWORDS = [
    "DIRECTORATE OF INFORMATION, PUBLIC RELATIONS AND LANGUAGES DEPARTMENT",
    "DIRECTORATE OF INFORMATION, PUBLIC RELATIONS AND LANGUAGES",
    "DIRECTORATE OF INFORMATION",
    "PUBLIC RELATIONS AND LANGUAGES"
]

def classify_pdf(pdf_path):
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text() or ""

        text_upper = text.upper().replace('\n', ' ').replace('\r', ' ')
        
        text_upper = re.sub(r'\s+', ' ', text_upper)
        #print(f"--- Extracted text from {pdf_path} ---\n{text_upper}\n--- END ---")

        def keyword_in_text(keywords):
            for kw in keywords:
                kw_norm = re.sub(r'\s+', ' ', kw.upper())
                if kw_norm in text_upper:
                    return True
            return False

        if keyword_in_text(DIPR_KEYWORDS):
            return "DIPR"
        elif keyword_in_text(CBC_KEYWORDS):
            return "DAVP"
        elif keyword_in_text(SAMVAD_KEYWORDS):
            return "SAMVAD"
        else:
            return "Others"

    except Exception as e:
        print(f"Error reading {pdf_path}: {e}")
        return "Others"



def classify_RO_catogory(SOURCE_FOLDER):
    for filename in os.listdir(SOURCE_FOLDER):
        if filename.lower().endswith(".pdf"):
            file_path = os.path.join(SOURCE_FOLDER, filename)
            category = classify_pdf(file_path)
            
            if category == "Others":
                logging.info(f"Classified as Others so classifying by checking the Content of file name {filename}")
                category = classify_pdf(file_path)
                logging.info(f"Classified as {category} based on filename: {filename}")
                if category == "Others":
                     logging.warning(f"Could not classify {filename} based on content or filename. Defaulting to Others.")   
                else:
                    return category
            else:
                return category                    
            print(f"{filename} → {category}")
    
    logging.info("Classification Completed!")
