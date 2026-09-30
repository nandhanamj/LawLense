import pymupdf
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

PDF_PATH = BASE_DIR / "data" / "raw" / "BNS.pdf"
OUTPUT_PATH = BASE_DIR / "data" / "processed" / "bns_raw.txt"


def main():

    doc = pymupdf.open(PDF_PATH)

    print(f"Total Pages: {len(doc)}")

    full_text = ""

    for page in doc:
        page_text = page.get_text()

        # Stop before the publication/digital-signature metadata
        if "UPLOADED BY THE MANAGER" in page_text:
            page_text = page_text.split("UPLOADED BY THE MANAGER", 1)[0]

        full_text += page_text
        full_text += "\n"

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(full_text)

    print("====================================")
    print("PDF Extraction Successful")
    print(f"Characters Extracted : {len(full_text)}")
    print(f"Saved To : {OUTPUT_PATH}")
    print("====================================")


if __name__ == "__main__":
    main()