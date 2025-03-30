import streamlit as st
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import re
import io
from zipfile import BadZipFile

st.title("EPUB Chapter Splitter")

uploaded_file = st.file_uploader("Upload an EPUB file", type=['epub'])

def extract_text_from_epub(book):
    full_text = []
    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        soup = BeautifulSoup(item.get_content(), 'html.parser')
        text = soup.get_text(separator='\n', strip=True)
        full_text.append(text)
    return '\n'.join(full_text)

def split_chapters(text):
    chapter_pattern = re.compile(r'^第(\d+)章', re.MULTILINE)
    matches = list(chapter_pattern.finditer(text))
    
    if not matches:
        return []
    
    chapters = []
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i+1].start() if i+1 < len(matches) else len(text)
        chapter_number = match.group(1)
        chapter_content = text[start:end].strip()
        chapters.append((chapter_number, chapter_content))
    return chapters

def create_new_epub(original_book, chapters):
    new_book = epub.EpubBook()
    
    # Copy metadata from original
    new_book.set_identifier(original_book.get_identifier())
    new_book.set_title(original_book.get_metadata('DC', 'title')[0][0])
    new_book.set_language(original_book.get_metadata('DC', 'language')[0][0])
    
    # Prepare author metadata
    authors = original_book.get_metadata('DC', 'creator')
    if authors:
        new_book.add_author(authors[0][0])
    
    # Create chapters
    epub_chapters = []
    for idx, (num, content) in enumerate(chapters):
        chapter = epub.EpubHtml(
            title=f'Chapter {num}',
            file_name=f'chap_{idx+1}.xhtml',
            lang='zh'
        )
        chapter.content = f'<h1>第{num}章</h1><p>' + content.replace('\n', '</p><p>') + '</p>'
        epub_chapters.append(chapter)
        new_book.add_item(chapter)
    
    # Define Table of Contents
    new_book.toc = tuple(epub_chapters)
    
    # Add default NCX and Nav files
    new_book.add_item(epub.EpubNcx())
    new_book.add_item(epub.EpubNav())
    
    # Create spine
    new_book.spine = epub_chapters
    
    return new_book

if uploaded_file:
    try:
        # Read the uploaded EPUB
        book = epub.read_epub(uploaded_file)
        text_content = extract_text_from_epub(book)
        
        # Split into chapters
        chapters = split_chapters(text_content)
        
        if not chapters:
            st.warning("No chapters detected! The book might not use '第X章' chapter markers.")
        else:
            st.success(f"Detected {len(chapters)} chapters. Creating new EPUB...")
            
            # Create new EPUB
            new_book = create_new_epub(book, chapters)
            
            # Generate download link
            buffer = io.BytesIO()
            epub.write_epub(buffer, new_book)
            buffer.seek(0)
            
            st.download_button(
                label="Download Split EPUB",
                data=buffer,
                file_name=f"split_{uploaded_file.name}",
                mime='application/epub+zip'
            )
            
    except BadZipFile:
        st.error("Invalid EPUB file! Please upload a valid EPUB.")
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
