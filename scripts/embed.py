import json
from pathlib import Path
import numpy as np
from sentence_transformers import SentenceTransformer

BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = BASE_DIR / "data" / "processed" / "bns_sections.json"
EMBEDDINGS_OUTPUT_FILE = BASE_DIR / "data" / "processed" / "bns_embeddings.npz"
METADATA_OUTPUT_FILE = BASE_DIR / "data" / "processed" / "bns_metadata.json"

MODEL_NAME = "intfloat/multilingual-e5-base"


def create_passage_text(section: dict) -> str:
    """Format section data into an E5 retrieval passage text."""
    act = section.get("act", "BNS")
    chapter = section.get("chapter", "")
    chapter_title = section.get("chapter_title", "")
    sec_num = section.get("section", "")
    content = section.get("content", "").strip()

    header_parts = [f"Act: {act}"]
    if chapter:
        header_parts.append(f"Chapter {chapter}" + (f" - {chapter_title}" if chapter_title else ""))
    header_parts.append(f"Section {sec_num}")

    header = ", ".join(header_parts)
    return f"passage: {header}\n{content}"


def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Input file not found at: {INPUT_FILE}. Ensure data/processed/bns_sections.json exists."
        )

    print(f"Reading sections from: {INPUT_FILE}")
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        sections = json.load(f)

    total_sections = len(sections)
    print(f"Total sections loaded: {total_sections}")

    # Prepare texts to embed and preserve mapping
    texts_to_embed = []
    metadata = []
    section_numbers = []

    for idx, sec in enumerate(sections):
        passage_text = create_passage_text(sec)
        texts_to_embed.append(passage_text)

        metadata.append({
            "index": idx,
            "act": sec.get("act", "BNS"),
            "chapter": sec.get("chapter", ""),
            "chapter_title": sec.get("chapter_title", ""),
            "section": sec.get("section", ""),
            "content": sec.get("content", ""),
            "embed_text": passage_text,
        })
        section_numbers.append(str(sec.get("section", "")))

    print(f"Loading embedding model: {MODEL_NAME}...")
    model = SentenceTransformer(MODEL_NAME)

    print("Generating normalized semantic embeddings...")
    embeddings = model.encode(
        texts_to_embed,
        batch_size=32,
        show_progress_bar=True,
        normalize_embeddings=True,
    )
    embeddings = np.array(embeddings, dtype=np.float32)

    # Ensure output directory exists
    EMBEDDINGS_OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Save embeddings to .npz
    np.savez_compressed(
        EMBEDDINGS_OUTPUT_FILE,
        embeddings=embeddings,
        section_numbers=np.array(section_numbers),
    )

    # Save metadata to .json
    with open(METADATA_OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=4, ensure_ascii=False)

    print("=" * 60)
    print("Embedding Generation Successful")
    print(f"Model Name            : {MODEL_NAME}")
    print(f"Sections Embedded     : {total_sections}")
    print(f"Embedding Dimension   : {embeddings.shape[1]}")
    print(f"Embeddings Output File: {EMBEDDINGS_OUTPUT_FILE}")
    print(f"Metadata Output File  : {METADATA_OUTPUT_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    main()
