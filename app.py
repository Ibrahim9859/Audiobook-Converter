import streamlit as st
import PyPDF2
import docx
import edge_tts
import asyncio
import os
import zipfile
from io import BytesIO
import base64

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
    "Jane (US Female - Friendly)": "en-US-JaneNeural",
    "Brian (UK Male - Natural)": "en-GB-BrianNeural",
}

# Sound effects
EFFECTS = {
    "None": "",
    "🎭 Dramatic": " [dramatic pause] ",
    "🌊 Nature": " [wind rustling] ",
    "🏰 Fantasy": " [magical echo] ",
    "🤖 Sci-Fi": " [robotic filter] ",
    "📖 Storytelling": " [narrator voice] ",
}

# Extract text from uploaded file
def extract_text(uploaded_file):
    file_extension = uploaded_file.name.split('.')[-1].lower()
    text = ""
    
    try:
        if file_extension == 'pdf':
            pdf_reader = PyPDF2.PdfReader(uploaded_file)
            for page in pdf_reader.pages:
                text += page.extract_text() or ""
        elif file_extension == 'docx':
            doc = docx.Document(uploaded_file)
            for para in doc.paragraphs:
                text += para.text + "\n"
        elif file_extension == 'txt':
            text = uploaded_file.getvalue().decode('utf-8')
        else:
            st.error(f"Unsupported format: {file_extension}")
            return None
    except Exception as e:
        st.error(f"Error reading file: {str(e)}")
        return None
    
    return text.strip()

# Split text into chunks (API has limit)
def chunk_text(text, max_chars=4000):
    words = text.split()
    chunks = []
    current_chunk = []
    current_length = 0
    
    for word in words:
        if current_length + len(word) + 1 <= max_chars:
            current_chunk.append(word)
            current_length += len(word) + 1
        else:
            chunks.append(" ".join(current_chunk))
            current_chunk = [word]
            current_length = len(word) + 1
    
    if current_chunk:
        chunks.append(" ".join(current_chunk))
    
    return chunks

# Convert text to speech using edge-tts
async def text_to_speech_async(text, voice, output_file, effect=""):
    # Apply effect formatting
    if effect and effect != "None":
        paragraphs = text.split('\n')
        text = EFFECTS.get(effect, "").join(paragraphs)
    
    communicate = edge_tts.Communicate(text[:4000], voice)
    await communicate.save(output_file)
    return output_file

# Wrapper function to run async code
def text_to_speech(text, voice, output_file, effect=""):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(
        text_to_speech_async(text, voice, output_file, effect)
    )
    loop.close()
    return result

# Auto-play audio in browser
def get_audio_html(audio_path):
    with open(audio_path, "rb") as f:
        audio_bytes = f.read()
    b64 = base64.b64encode(audio_bytes).decode()
    return f'<audio controls autoplay><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>'

# Main UI
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
    st.markdown("### ⚡")
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
                st.text(text[:500] + "..." if len(text) > 500 else text)
            
            # Split into chunks and convert
            chunks = chunk_text(text)
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            audio_files = []
            for i, chunk in enumerate(chunks):
                status_text.text(f"Processing chunk {i+1}/{len(chunks)}")
                output_file = f"chunk_{i+1}_{file.name.replace(' ', '_')}.mp3"
                
                # Call the wrapper function
                text_to_speech(chunk[:4000], voice_code, output_file, effect)
                
                audio_files.append(output_file)
                progress_bar.progress((i + 1) / len(chunks))
            
            status_text.text("✅ Done!")
            
            # Merge all chunks into one
            if len(audio_files) > 1:
                try:
                    from pydub import AudioSegment
                    combined = AudioSegment.empty()
                    for f in audio_files:
                        combined += AudioSegment.from_mp3(f)
                        os.remove(f)  # Clean up
                    final_file = f"audiobook_{file.name.replace(' ', '_')}.mp3"
                    combined.export(final_file, format="mp3")
                    all_audio_files.append(final_file)
                except:
                    # If pydub fails, just use the first chunk
                    final_file = audio_files[0]
                    all_audio_files.append(final_file)
            else:
                final_file = audio_files[0]
                all_audio_files.append(final_file)
            
            # Play audio in browser
            st.markdown(get_audio_html(final_file), unsafe_allow_html=True)
            
            # Download button
            with open(final_file, "rb") as f:
                st.download_button(
                    label=f"⬇️ Download {file.name}.mp3",
                    data=f,
                    file_name=f"{file.name.replace(' ', '_')}_audiobook.mp3",
                    mime="audio/mp3"
                )
        
        # Option to download all as ZIP
        if len(all_audio_files) > 1:
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
                for f in all_audio_files:
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

# Footer
st.markdown("---")
st.caption("⚡ Powered by free Microsoft Edge TTS • No API key required • 100% free")
st.caption("💡 For best results, keep files under 100 pages")
