import streamlit as st
import PyPDF2
import docx
import requests
import os
import zipfile
from io import BytesIO
import base64
import re
import json
import time

# Page config
st.set_page_config(page_title="Free Audiobook Converter", page_icon="📚", layout="wide")

st.title("📚 Free Audiobook Converter")
st.markdown("Convert PDF, Word, or Text files to AI-narrated audiobooks instantly!")

# Voice options (using a free API)
VOICE_OPTIONS = {
    "Female (US)": "en-US-JennyNeural",
    "Male (US)": "en-US-GuyNeural",
    "Female (UK)": "en-GB-SoniaNeural",
    "Male (UK)": "en-GB-RyanNeural",
}

# ========== TEXT EXTRACTION ==========
def extract_text_from_pdf(uploaded_file):
    """Extract text from PDF"""
    text = ""
    try:
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        num_pages = len(pdf_reader.pages)
        st.info(f"📄 Found {num_pages} pages")
        
        for page_num, page in enumerate(pdf_reader.pages, 1):
            try:
                page_text = page.extract_text()
                if page_text:
                    text += page_text.strip() + " "
            except:
                continue
                
        if not text or len(text.strip()) < 10:
            st.warning("⚠️ Could not extract text. PDF may be scanned.")
            return None
            
    except Exception as e:
        st.error(f"Error reading PDF: {str(e)}")
        return None
    
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def extract_text_from_docx(uploaded_file):
    """Extract text from DOCX"""
    try:
        doc = docx.Document(uploaded_file)
        text = ""
        for para in doc.paragraphs:
            if para.text:
                text += para.text + " "
        return text.strip()
    except:
        return None

def extract_text_from_txt(uploaded_file):
    """Extract text from TXT"""
    try:
        text = uploaded_file.getvalue().decode('utf-8', errors='ignore')
        return text.strip()
    except:
        return None

def extract_text(uploaded_file):
    """Main extraction function"""
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

# ========== TEXT TO SPEECH USING FREE API ==========
def text_to_speech_edge(text, voice, output_file):
    """Convert text to speech using Microsoft Edge TTS (free)"""
    try:
        # This uses the free edge-tts Python package
        import edge_tts
        import asyncio
        
        async def tts():
            communicate = edge_tts.Communicate(text[:3000], voice)
            await communicate.save(output_file)
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(tts())
        loop.close()
        
        if os.path.exists(output_file) and os.path.getsize(output_file) > 1000:
            return True
        return False
    except Exception as e:
        st.warning(f"Edge TTS error: {str(e)}")
        return False

def text_to_speech_alternative(text, output_file):
    """Alternative TTS using a free API (no installation needed)"""
    try:
        # Use a free TTS API
        url = "https://api.streamelements.com/kappa/v2/speech"
        
        headers = {
            "Content-Type": "application/json"
        }
        
        data = {
            "voice": "Brian",
            "text": text[:2000]  # Limit text length
        }
        
        response = requests.post(url, json=data, headers=headers)
        
        if response.status_code == 200:
            with open(output_file, 'wb') as f:
                f.write(response.content)
            return os.path.getsize(output_file) > 1000
        return False
    except:
        return False

def text_to_speech_google(text, output_file):
    """Alternative using Google TTS (free, no API key needed)"""
    try:
        # Using a free Google TTS endpoint
        import base64
        
        # Simple gTTS replacement using requests
        url = f"https://translate.google.com/translate_tts"
        
        params = {
            "ie": "UTF-8",
            "q": text[:200],
            "tl": "en",
            "client": "tw-ob"
        }
        
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            with open(output_file, 'wb') as f:
                f.write(response.content)
            return os.path.getsize(output_file) > 1000
        return False
    except:
        return False

# ========== MAIN CONVERSION ==========
def convert_text_to_speech(text, voice, output_file, max_retries=3):
    """Try multiple TTS methods"""
    
    # Method 1: Edge TTS (best quality)
    if text_to_speech_edge(text, voice, output_file):
        return True
    
    # Method 2: Alternative API
    if text_to_speech_alternative(text, output_file):
        return True
    
    # Method 3: Google TTS (fallback)
    if text_to_speech_google(text, output_file):
        return True
    
    return False

# ========== AUDIO HELPERS ==========
def get_audio_html(audio_path):
    """Generate audio player HTML"""
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
    """Merge audio files"""
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
    except:
        return valid_files[0]

# ========== UI ==========
st.markdown("---")
st.info("💡 **Upload a PDF, DOCX, or TXT file to convert it to an audiobook**")

uploaded_files = st.file_uploader(
    "📤 Upload files", 
    type=['pdf', 'docx', 'txt'], 
    accept_multiple_files=True
)

col1, col2 = st.columns(2)
with col1:
    voice = st.selectbox("🎤 Choose Voice", list(VOICE_OPTIONS.keys()))
with col2:
    st.markdown("### ⚡")
    process_btn = st.button("🚀 Convert to Audiobook", type="primary", use_container_width=True)

if uploaded_files and process_btn:
    voice_code = VOICE_OPTIONS[voice]
    
    with st.spinner("📖 Processing files..."):
        all_audio_files = []
        
        for file in uploaded_files:
            st.subheader(f"🎧 {file.name}")
            
            # Extract text
            text = extract_text(file)
            if not text:
                st.warning(f"Skipping {file.name} - no readable text found")
                continue
            
            # Show preview
            with st.expander("📄 Text Preview"):
                preview = text[:300] + "..." if len(text) > 300 else text
                st.text(preview)
                st.caption(f"Total characters: {len(text)}")
            
            # Process text
            if len(text) > 3000:
                # Split into chunks
                words = text.split()
                chunks = []
                for i in range(0, len(words), 500):
                    chunks.append(" ".join(words[i:i+500]))
                st.info(f"Split into {len(chunks)} chunks")
            else:
                chunks = [text]
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            audio_files = []
            total_chunks = len(chunks)
            
            for i, chunk in enumerate(chunks):
                status_text.text(f"Converting chunk {i+1}/{total_chunks}...")
                output_file = f"chunk_{i+1}_{file.name.replace(' ', '_')}.mp3"
                
                success = convert_text_to_speech(chunk, voice_code, output_file)
                
                if success:
                    audio_files.append(output_file)
                else:
                    status_text.text(f"⚠️ Chunk {i+1} failed")
                
                progress_bar.progress((i + 1) / total_chunks)
            
            if not audio_files:
                st.error("❌ No audio could be generated")
                continue
            
            # Final audio
            if len(audio_files) > 1:
                final_file = f"audiobook_{file.name.replace(' ', '_')}.mp3"
                merged = merge_audio_files(audio_files, final_file)
                final_file = merged if merged else audio_files[0]
            else:
                final_file = audio_files[0]
            
            if final_file and os.path.exists(final_file):
                all_audio_files.append(final_file)
                
                # Play and download
                st.markdown(get_audio_html(final_file), unsafe_allow_html=True)
                
                with open(final_file, "rb") as f:
                    st.download_button(
                        label=f"⬇️ Download {file.name}.mp3",
                        data=f,
                        file_name=f"{file.name.replace(' ', '_')}_audiobook.mp3",
                        mime="audio/mp3"
                    )
        
        st.success("🎉 Conversion complete!")

# ========== FOOTER ==========
st.markdown("---")
st.caption("⚡ Powered by free TTS APIs • No API key required • 100% free")

with st.expander("❓ Troubleshooting"):
    st.markdown("""
    **Why PDFs might not work:**
    - 📄 **Scanned/Image PDFs** - Can't extract text. Use OCR first.
    - 🔒 **Encrypted PDFs** - Need password to read.
    - 📝 **No selectable text** - PDF is just images.
    
    **Solutions:**
    1. Use text-based PDFs (try selecting text with mouse)
    2. Convert scanned PDF using Google Drive → Open with Google Docs
    3. Use a different file format (DOCX, TXT)
    """)
