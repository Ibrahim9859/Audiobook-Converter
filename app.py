import streamlit as st
import PyPDF2
import docx
import edge_tts
import asyncio
import os
import zipfile
from io import BytesIO
import base64
import re

# Page config
st.set_page_config(page_title="Free Audiobook Converter", page_icon="📚", layout="wide")

st.title("📚 Free Audiobook Converter")
st.markdown("Convert PDF, Word, or Text files to AI-narrated audiobooks instantly!")

# Voice options (all free!)
VOICE_OPTIONS = {
    "Jenny (US Female)": "en-US-JennyNeural",
    "Guy (US Male)": "en-US-GuyNeural",
    "Sonia (UK Female)": "en-GB-SoniaNeural",
    "Ryan (UK Male)": "en-GB-RyanNeural",
    "Annie (US Female - Storytelling)": "en-US-AnnieNeural",
    "Davis (US Male - Conversational)": "en-US-DavisNeural",
}

# Sound effects
EFFECTS = {
    "None": "",
    "🎭 Dramatic": " Dramatic pause. ",
    "🌊 Nature": " A gentle breeze. ",
    "🏰 Fantasy": " A magical echo. ",
}

# ========== IMPROVED PDF EXTRACTION ==========
def extract_text_from_pdf(uploaded_file):
    """Extract text from PDF with multiple methods"""
    text = ""
    try:
        # Method 1: Standard PyPDF2
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        num_pages = len(pdf_reader.pages)
        
        st.info(f"📄 Found {num_pages} pages in PDF")
        
        for page_num, page in enumerate(pdf_reader.pages, 1):
            try:
                page_text = page.extract_text()
                if page_text and len(page_text.strip()) > 0:
                    text += page_text.strip() + " "
                else:
                    st.warning(f"Page {page_num} appears to be empty or image-based")
            except Exception as e:
                st.warning(f"Could not extract text from page {page_num}: {str(e)}")
                continue
        
        # If no text found, try alternative extraction
        if len(text.strip()) < 50:
            st.warning("⚠️ PDF may be scanned or image-based. Try converting to text first using OCR.")
            return None
            
    except Exception as e:
        st.error(f"Error reading PDF: {str(e)}")
        return None
    
    # Clean text
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'[^\w\s.,!?-]', ' ', text)  # Remove weird characters
    
    if len(text) < 10:
        st.error("❌ Could not extract readable text from this PDF. It may be scanned or encrypted.")
        return None
    
    return text

def extract_text_from_docx(uploaded_file):
    """Extract text from DOCX files"""
    try:
        doc = docx.Document(uploaded_file)
        text = ""
        for para in doc.paragraphs:
            if para.text:
                text += para.text + " "
        return text.strip()
    except Exception as e:
        st.error(f"Error reading DOCX: {str(e)}")
        return None

def extract_text_from_txt(uploaded_file):
    """Extract text from TXT files"""
    try:
        text = uploaded_file.getvalue().decode('utf-8', errors='ignore')
        return text.strip()
    except Exception as e:
        st.error(f"Error reading TXT: {str(e)}")
        return None

# ========== MAIN EXTRACTION FUNCTION ==========
def extract_text(uploaded_file):
    """Extract text from any supported file type"""
    file_extension = uploaded_file.name.split('.')[-1].lower()
    
    if file_extension == 'pdf':
        return extract_text_from_pdf(uploaded_file)
    elif file_extension == 'docx':
        return extract_text_from_docx(uploaded_file)
    elif file_extension == 'txt':
        return extract_text_from_txt(uploaded_file)
    else:
        st.error(f"Unsupported format: {file_extension}")
        return None

# ========== TEXT PROCESSING ==========
def clean_text_for_tts(text):
    """Clean text for better TTS conversion"""
    # Remove URLs
    text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
    # Remove email addresses
    text = re.sub(r'\S+@\S+', '', text)
    # Remove excessive punctuation
    text = re.sub(r'[.]+', '.', text)
    # Remove numbers that don't add value (keep years, etc.)
    text = re.sub(r'\d+\.?\d*%', 'percent', text)
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def chunk_text_for_tts(text, max_chars=3000):
    """Split text into chunks suitable for TTS"""
    if len(text) <= max_chars:
        return [text]
    
    chunks = []
    # Split by sentences first
    sentences = re.split(r'(?<=[.!?])\s+', text)
    current_chunk = ""
    
    for sentence in sentences:
        if len(current_chunk) + len(sentence) + 1 <= max_chars:
            current_chunk += sentence + " "
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence + " "
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    # If still too many chunks, split by words
    if len(chunks) > 20:
        all_words = text.split()
        chunks = []
        for i in range(0, len(all_words), 500):
            chunks.append(" ".join(all_words[i:i+500]))
    
    return chunks

# ========== TTS CONVERSION ==========
async def text_to_speech_async(text, voice, output_file, effect="", retries=2):
    """Convert text to speech with retry logic"""
    # Clean text
    text = clean_text_for_tts(text)
    
    if not text or len(text) < 3:
        text = "This section could not be processed."
    
    # Apply effect
    if effect and effect != "None":
        text = EFFECTS.get(effect, "") + text
    
    # Truncate if needed
    if len(text) > 4000:
        text = text[:4000]
    
    for attempt in range(retries):
        try:
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(output_file)
            
            # Verify file was created
            if os.path.exists(output_file) and os.path.getsize(output_file) > 1000:
                return output_file
            else:
                raise Exception("Empty or invalid audio file")
                
        except Exception as e:
            if attempt < retries - 1:
                await asyncio.sleep(2)
                continue
            else:
                # Create fallback audio
                try:
                    fallback = edge_tts.Communicate("This part could not be read.", voice)
                    await fallback.save(output_file)
                except:
                    # Create empty file
                    with open(output_file, 'wb') as f:
                        f.write(b'')
                return output_file
    
    return output_file

def text_to_speech(text, voice, output_file, effect=""):
    """Wrapper for TTS function"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            text_to_speech_async(text, voice, output_file, effect)
        )
        loop.close()
        return result
    except Exception as e:
        st.error(f"Speech conversion error: {str(e)}")
        try:
            with open(output_file, 'wb') as f:
                f.write(b'')
        except:
            pass
        return output_file

# ========== AUDIO PROCESSING ==========
def get_audio_html(audio_path):
    """Generate HTML for audio playback"""
    if not os.path.exists(audio_path) or os.path.getsize(audio_path) < 100:
        return "<p>⚠️ No audio generated</p>"
    
    try:
        with open(audio_path, "rb") as f:
            audio_bytes = f.read()
        b64 = base64.b64encode(audio_bytes).decode()
        return f'<audio controls autoplay><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>'
    except:
        return "<p>⚠️ Error loading audio</p>"

def merge_audio_files(audio_files, output_file):
    """Merge multiple audio files into one"""
    valid_files = [f for f in audio_files if os.path.exists(f) and os.path.getsize(f) > 100]
    
    if not valid_files:
        return None
    
    if len(valid_files) == 1:
        return valid_files[0]
    
    try:
        from pydub import AudioSegment
        combined = AudioSegment.empty()
        for f in valid_files:
            try:
                audio = AudioSegment.from_mp3(f)
                combined += audio
            except:
                continue
        combined.export(output_file, format="mp3")
        return output_file
    except Exception as e:
        st.warning(f"Could not merge files: {str(e)}")
        return valid_files[0]  # Return first valid file

# ========== MAIN UI ==========
st.markdown("---")
st.info("💡 **Tip:** For best results with PDFs, make sure they contain selectable text (not scanned images).")

uploaded_files = st.file_uploader(
    "📤 Upload files (PDF, DOCX, TXT)", 
    type=['pdf', 'docx', 'txt'], 
    accept_multiple_files=True
)

col1, col2, col3 = st.columns(3)
with col1:
    voice = st.selectbox("🎤 Choose Voice", list(VOICE_OPTIONS.keys()))
with col2:
    effect = st.selectbox("✨ Sound Effect", list(EFFECTS.keys()))
with col3:
    process_btn = st.button("🚀 Convert to Audiobook", type="primary", use_container_width=True)

if uploaded_files and process_btn:
    voice_code = VOICE_OPTIONS[voice]
    
    with st.spinner("📖 Extracting text and generating audiobooks..."):
        all_audio_files = []
        
        for file in uploaded_files:
            st.subheader(f"🎧 {file.name}")
            
            # Extract text
            text = extract_text(file)
            if not text:
                st.warning(f"Skipping {file.name} - no text found")
                continue
            
            # Show preview
            with st.expander("📄 Text Preview"):
                preview = text[:500] + "..." if len(text) > 500 else text
                st.text(preview)
                st.caption(f"Total characters: {len(text)}")
                st.caption(f"Estimated audio length: ~{len(text)//15} seconds")
            
            # Split into chunks
            chunks = chunk_text_for_tts(text)
            st.info(f"Split into {len(chunks)} chunks for processing")
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            audio_files = []
            total_chunks = len(chunks)
            failed_chunks = 0
            
            for i, chunk in enumerate(chunks):
                status_text.text(f"Processing chunk {i+1}/{total_chunks}...")
                output_file = f"chunk_{i+1}_{file.name.replace(' ', '_')}.mp3"
                
                # Convert
                text_to_speech(chunk, voice_code, output_file, effect)
                
                # Check result
                if os.path.exists(output_file) and os.path.getsize(output_file) > 100:
                    audio_files.append(output_file)
                else:
                    failed_chunks += 1
                    status_text.text(f"⚠️ Chunk {i+1} failed, continuing...")
                
                progress_bar.progress((i + 1) / total_chunks)
            
            if not audio_files:
                st.error("❌ No audio could be generated for this file")
                continue
            
            if failed_chunks > 0:
                st.warning(f"⚠️ {failed_chunks} chunks failed, but {len(audio_files)} succeeded")
            
            status_text.text("✅ Done!")
            
            # Process final audio
            if len(audio_files) > 1:
                final_file = f"audiobook_{file.name.replace(' ', '_')}.mp3"
                merged = merge_audio_files(audio_files, final_file)
                if merged and os.path.exists(merged):
                    final_file = merged
                else:
                    final_file = audio_files[0]
            else:
                final_file = audio_files[0]
            
            if final_file and os.path.exists(final_file) and os.path.getsize(final_file) > 100:
                all_audio_files.append(final_file)
                
                # Play audio
                st.markdown(get_audio_html(final_file), unsafe_allow_html=True)
                
                # Download button
                with open(final_file, "rb") as f:
                    st.download_button(
                        label=f"⬇️ Download {file.name}.mp3",
                        data=f,
                        file_name=f"{file.name.replace(' ', '_')}_audiobook.mp3",
                        mime="audio/mp3"
                    )
        
        # Download all as ZIP
        if len(all_audio_files) > 1:
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
                for f in all_audio_files:
                    if os.path.exists(f):
                        zip_file.write(f)
            zip_buffer.seek(0)
            
            st.download_button(
                label="📦 Download All as ZIP",
                data=zip_buffer,
                file_name="audiobooks.zip",
                mime="application/zip",
                type="primary"
            )
    
    st.success("🎉 All audiobooks created successfully!")

# ========== FOOTER ==========
st.markdown("---")
st.caption("⚡ Powered by free Microsoft Edge TTS • No API key required • 100% free")

# Add help section
with st.expander("❓ Need help with PDFs?"):
    st.markdown("""
    **Why some PDFs don't work:**
    - 📄 **Scanned PDFs** - These are images, not text. Use an OCR tool first.
    - 🔒 **Encrypted PDFs** - Can't be read without a password.
    - 🖼️ **Image-based PDFs** - Same as scanned, no selectable text.
    
    **Solutions:**
    1. Use a PDF with selectable text (Ctrl+A to select all text)
    2. Convert scanned PDF to text using Google Drive or Adobe
    3. Try a DOCX or TXT file instead
    """)

st.caption("💡 For best results, use text-based PDFs (not scanned documents)")
