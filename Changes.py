# -------- MULTI CLIENT DETECTION -----------------------------------------
#------At the bigining of extract_invoice_data-----

    client_rows = re.findall(r'\n\s*\d+\s+[A-Za-z&\s]+', text)
    is_multi_client = len(client_rows) > 1

#-----Remark section changed--------
remark_match = re.search( r'Remarks?\s*(.*?)\s*B\.\s*Advertisement',text,re.IGNORECASE | re.DOTALL)
    if remark_match:
        remark = remark_match.group(1)
        remark = remark.replace('\n', ' ')
        remark = re.sub(r'\s+', ' ', remark).strip()
        data["RO_REMARKS"] = remark.upper()
    else:
        data["RO_REMARKS"] = ""

#------------MULTIPLE CLIENT HANDLING --------
    if is_multi_client:
        data["RO_CLIENT_NAME"] = "Multi Department"
        data["CLIENT_CODE"] = "MU145"
        data["RO_CLIENT_CODE"] = "-"
        data["GSTIN"] = "-"
    else:   # -------- EXISTING CLIENT LOGIC --------

    #---------Size section regex code--------------------

     size_match = re.search(r'/\s*([\d]+(?:\.\d+)?)\s*(?=\(\s*Sq|Rs)', text)
