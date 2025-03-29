import streamlit as st
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import re
import io

st.title("EPUB Chapter Splitter")

uploaded_file = st.file_uploader("Upload an EPUB file", type=['epub'])

def extract_text_from_epub(book):
    full_text = []
    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            soup = BeautifulSoup(item.get_content(), 'html.parser')
            text = soup.get_text(separator='\n', strip=True)
            full_text.append(text)
    return '\n'.join(full_text)

def split_chapters(text):
    chapter_pattern = re.compile(r'^第(\d+)章', re.MULTILINE)
    matches = list(chapter_pattern.finditer(text))
    
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
    new_book.set_title(original_book.get_metadata('DC', 'title')[0][0] 
                      if original_book.get_metadata('DC', 'title') else 'Untitled')
    new_book.set_language('zh')
    
    # Add CSS styling
    style = epub.EpubItem(uid="style_nav", file_name="style.css", 
                         media_type="text/css", content='''
        body { font-family: Arial, sans-serif; line-height: 1.6; }
        h1 { page-break-before: always; }
    ''')
    new_book.add_item(style)
    
    # Create chapters
    epub_chapters = []
    for number, content in chapters:
        chapter = epub.EpubHtml(title=f'第{number}章', 
                               file_name=f'chapter_{number}.xhtml', 
                               lang='zh')
        chapter.content = f'<h1>第{number}章</h1><div>{content.replace("\n", "<br/>")}</div>'
        chapter.add_item(style)
        new_book.add_item(chapter)
        epub_chapters.append(chapter)
    
    new_book.toc = tuple(epub_chapters)
    new_book.spine = epub_chapters
    new_book.add_item(epub.EpubNcx())
    new_book.add_item(epub.EpubNav())
    
    return new_book

if uploaded_file is not None:
    try:
        # Process EPUB
        original_book = epub.read_epub(uploaded_file)
        text_content = extract_text_from_epub(original_book)
        chapters = split_chapters(text_content)
        
        if not chapters:
            st.error("No chapters found! Ensure your EPUB contains lines like '第1章', '第2章'")
        else:
            new_epub = create_new_epub(original_book, chapters)
            
            # Prepare download
            buffer = io.BytesIO()
            epub.write_epub(buffer, new_epub, {})
            buffer.seek(0)
            
            st.success(f"Successfully created {len(chapters)} chapters!")
            st.download_button("Download Processed EPUB", 
                             data=buffer, 
                             file_name='processed.epub',
                             mime='application/epub+zip')
    except Exception as e:
        st.error(f"Error processing EPUB: {str(e)}")