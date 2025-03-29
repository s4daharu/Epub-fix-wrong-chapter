import re
import io
import streamlit as st
import tempfile
from ebooklib import epub, ITEM_DOCUMENT
from bs4 import BeautifulSoup

st.title("EPUB Chapter Fixer")

st.markdown("""
This app accepts an EPUB file, extracts text, splits it into chapters by detecting chapter markers (e.g., “第1章”, “第2章”, etc.), and generates a corrected EPUB.
""")

uploaded_file = st.file_uploader("Upload an EPUB file", type=["epub"])

def extract_text_from_epub(uploaded_file):
    """
    Extracts text from an EPUB file by writing it to a temporary file and then parsing all document items.
    """
    # Reset the file pointer.
    uploaded_file.seek(0)
    
    # Write the uploaded file to a temporary file so that ebooklib can read it by path.
    with tempfile.NamedTemporaryFile(delete=False, suffix='.epub') as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name

    # Read the epub from the temporary file path.
    book = epub.read_epub(tmp_path)
    full_text = ""

    # Iterate over all document items in the EPUB.
    for item in book.get_items_of_type(ITEM_DOCUMENT):
        # Use get_content() to obtain the raw HTML content.
        content = item.get_content()
        # Parse the HTML content.
        soup = BeautifulSoup(content, "html.parser")
        text = soup.get_text(separator="\n")
        full_text += text + "\n"

    return full_text

def split_into_chapters(text):
    """
    Splits the full text into chapters by finding lines starting with a chapter marker.
    Assumes chapter headings match the pattern '第<number>章' at the start of a line.
    """
    pattern = r'(?m)^(第\d+章.*)$'
    parts = re.split(pattern, text)

    chapters = []
    # If there's introductory text before the first chapter marker, capture it.
    if parts[0].strip():
        chapters.append(("Intro", parts[0]))

    # Process remaining parts in pairs: (chapter heading, chapter content)
    for i in range(1, len(parts), 2):
        heading = parts[i].strip()
        content = parts[i+1] if i+1 < len(parts) else ""
        chapters.append((heading, content))
    
    return chapters

def create_new_epub(chapters):
    """
    Creates a new EPUB book from the list of chapters.
    Each chapter is added as a separate section.
    """
    book = epub.EpubBook()
    book.set_title("Fixed EPUB")
    book.add_author("Auto-generated")

    epub_chapters = []
    for idx, (heading, content) in enumerate(chapters):
        # Use the chapter heading if it matches the expected pattern; otherwise, assign a default chapter title.
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
    try:
        full_text = extract_text_from_epub(uploaded_file)
    except Exception as e:
        st.error(f"Error reading EPUB file: {e}")
    else:
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