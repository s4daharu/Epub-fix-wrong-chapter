import re
import io
import streamlit as st
from ebooklib import epub
from bs4 import BeautifulSoup

st.title("EPUB Chapter Fixer")

st.markdown("""
This app accepts an EPUB file, extracts text, splits it into chapters by detecting chapter markers (e.g., “第1章”, “第2章”, etc.), and generates a corrected EPUB.
""")

uploaded_file = st.file_uploader("Upload an EPUB file", type=["epub"])

def extract_text_from_epub(uploaded_file):
    """Extracts text from an EPUB file using ebooklib."""
    book = epub.read_epub(io.BytesIO(uploaded_file.read()))  # Ensure correct file handling
    full_text = ""
    
    for item in book.get_items():
        if item.get_type() == epub.EpubHtml:
            soup = BeautifulSoup(item.get_body_content(), "html.parser")
            text = soup.get_text(separator="\n")
            full_text += text + "\n"
    
    return full_text

def split_into_chapters(text):
    """
    Splits text into chapters based on lines that start with '第XX章'.
    """
    pattern = r'(?m)^(第\d+章.*)$'
    parts = re.split(pattern, text)

    chapters = []
    if parts[0].strip():
        chapters.append(("Intro", parts[0]))

    for i in range(1, len(parts), 2):
        heading = parts[i].strip()
        content = parts[i+1] if i+1 < len(parts) else ""
        chapters.append((heading, content))
    
    return chapters

def create_new_epub(chapters):
    """Creates a new EPUB with corrected chapters."""
    book = epub.EpubBook()
    book.set_title("Fixed EPUB")
    book.add_author("Auto-generated")

    epub_chapters = []
    for idx, (heading, content) in enumerate(chapters):
        chap_title = heading if re.match(r"第\d+章", heading) else f"Chapter {idx}"
        chapter_html = epub.EpubHtml(title=chap_title, file_name=f'chap_{idx}.xhtml', lang='zh')
        chapter_content = f"<h1>{heading}</h1>\n<p>{content.replace(chr(10), '</p><p>')}</p>"
        chapter_html.content = chapter_content
        book.add_item(chapter_html)
        epub_chapters.append(chapter_html)

    book.toc = tuple(epub_chapters)
    book.spine = ['nav'] + epub_chapters

    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    out = io.BytesIO()
    epub.write_epub(out, book)
    out.seek(0)
    return out

if uploaded_file:
    full_text = extract_text_from_epub(uploaded_file)
    
    if not full_text.strip():
        st.error("No textual content could be extracted from the EPUB.")
    else:
        st.markdown("### Extracted Text Preview")
        st.text_area("Preview (first 1000 characters)", full_text[:1000], height=200)

        chapters = split_into_chapters(full_text)
        st.write(f"Detected {len(chapters)} chapters.")

        for idx, (heading, _) in enumerate(chapters):
            st.write(f"{idx+1}. {heading}")

        if st.button("Generate Fixed EPUB"):
            new_epub_io = create_new_epub(chapters)
            st.download_button(label="Download Fixed EPUB",
                               data=new_epub_io,
                               file_name="fixed_book.epub",
                               mime="application/epub+zip")