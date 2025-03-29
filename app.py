import re
import io
import streamlit as st
from ebooklib import epub
from bs4 import BeautifulSoup

st.title("EPUB Chapter Splitter")

st.markdown("""
This app accepts an EPUB file, extracts the full text, splits it into chapters by detecting chapter markers (e.g., “第1章”, “第2章”, etc.), and then creates a new EPUB where each chapter is a separate section.
""")

uploaded_file = st.file_uploader("Upload an EPUB file", type=["epub"])

def extract_text_from_epub(epub_file):
    """Extract text from each document item in the epub and join into one text."""
    book = epub.read_epub(epub_file)
    full_text = ""
    # We assume items of type DOCUMENT contain the text.
    for item in book.get_items():
        if item.get_type() == epub.EpubHtml:
            # Get HTML content and convert to plain text.
            soup = BeautifulSoup(item.get_body_content(), "html.parser")
            text = soup.get_text(separator="\n")
            full_text += text + "\n"
    return full_text

def split_into_chapters(text):
    """
    Split text into chapters using a regex that finds lines starting with chapter markers.
    This regex assumes that a chapter heading looks like "第<number>章" at the beginning of a line.
    """
    # Use a regex with a capture group so we keep the chapter heading.
    # The (?m) flag makes ^ match the start of each line.
    pattern = r'(?m)^(第\d+章.*)$'
    parts = re.split(pattern, text)
    
    chapters = []
    # If the file starts with a chapter heading, the first element might be empty.
    # The list will be like: [pre_text, chapter_heading, chapter_content, chapter_heading, chapter_content, ...]
    if parts[0].strip() != "":
        # Optional: if there is some introductory text before the first chapter, add it as "Intro"
        chapters.append(("Intro", parts[0]))
    
    # Iterate over remaining parts pairwise: (heading, content)
    for i in range(1, len(parts), 2):
        heading = parts[i].strip()
        content = parts[i+1] if i+1 < len(parts) else ""
        chapters.append((heading, content))
    return chapters

def create_new_epub(chapters):
    """Create a new EPUB book from chapters, where each chapter is an epub.EpubHtml item."""
    book = epub.EpubBook()
    book.set_title("New EPUB with Chapters")
    book.add_author("Auto-generated")
    
    epub_chapters = []
    for idx, (heading, content) in enumerate(chapters):
        # Use the chapter marker as title if possible, else fallback to Chapter {idx}
        chap_title = heading if re.match(r"第\d+章", heading) else f"Chapter {idx}"
        chapter_html = epub.EpubHtml(title=chap_title, file_name=f'chap_{idx}.xhtml', lang='zh')
        # Wrap content in minimal HTML. Here, we use the chapter heading as an <h1> if it is a marker.
        chapter_content = f"<h1>{heading}</h1>\n<p>{content.replace(chr(10), '</p><p>')}</p>"
        chapter_html.content = chapter_content
        book.add_item(chapter_html)
        epub_chapters.append(chapter_html)
    
    # Define Table of Contents and Spine order.
    book.toc = tuple(epub_chapters)
    book.spine = ['nav'] + epub_chapters
    
    # Add default NCX and Nav file.
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    
    # Write to a bytes buffer.
    out = io.BytesIO()
    epub.write_epub(out, book)
    out.seek(0)
    return out

if uploaded_file:
    # Read and extract text.
    full_text = extract_text_from_epub(uploaded_file)
    if not full_text.strip():
        st.error("No textual content could be extracted from the EPUB.")
    else:
        st.markdown("### Extracted text preview")
        st.text_area("Preview (first 1000 characters)", full_text[:1000], height=200)
        
        # Split into chapters based on chapter markers.
        chapters = split_into_chapters(full_text)
        st.write(f"Found {len(chapters)} chapters (or sections).")
        
        # Show list of chapter headings.
        for idx, (heading, _) in enumerate(chapters):
            st.write(f"{idx+1}. {heading}")
        
        # Create new epub
        if st.button("Create new EPUB"):
            new_epub_io = create_new_epub(chapters)
            st.download_button(label="Download new EPUB",
                               data=new_epub_io,
                               file_name="new_chapters.epub",
                               mime="application/epub+zip")