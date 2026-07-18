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
import json
import tempfile

# Page config
st.set_page_config(
    page_title="Storytelling Audiobook Converter", 
    page_icon="📚", 
    layout="wide"
)

st.title("📚 Storytelling Audiobook Converter")
st.markdown("Transform PDFs into immersive audiobooks with natural narration and sound effects!")

# ========== VOICE OPTIONS WITH STORYTELLING VOICES ==========
VOICE_OPTIONS = {
    "📖 Storyteller (US Female)": "en-US-AriaNeural",
    "🎭 Narrator (US Male)": "en-US-GuyNeural", 
    "📚 Audiobook (UK Female)": "en-GB-SoniaNeural",
    "🎪 Dramatic (US Male)": "en-US-DavisNeural",
    "🧚 Fairy Tale (US Female)": "en-US-JennyNeural",
}

# ========== STORYTELLING STYLES ==========
STORY_STYLES = {
    "📖 Classic Storytelling": {
        "intro": "Once upon a time... ",
        "pacing": "slow",
        "pause": "... ",
        "style": "narrative"
    },
    "🎭 Dramatic": {
        "intro": "In a world... ",
        "pacing": "medium",
        "pause": "... ",
        "style": "dramatic"
    },
    "🧙 Fantasy": {
        "intro": "In the realm of... ",
        "pacing": "slow",
        "pause": "... ",
        "style": "epic"
    },
    "🤖 Sci-Fi": {
        "intro": "In the future... ",
        "pacing": "medium",
        "pause": "... ",
        "style": "technical"
    },
    "📚 Educational": {
        "intro": "Let's learn about... ",
        "pacing": "normal",
        "pause": ". ",
        "style": "informative"
    }
}

# ========== SOUND EFFECTS (Text-based) ==========
SOUND_EFFECTS = {
    "None": {
        "description": "No effects",
        "transitions": [],
        "emphasis": []
    },
    "🌊 Nature & Ambient": {
        "description": "Forest, rain, wind sounds",
        "transitions": ["A gentle breeze rustles... ", "Raindrops patter softly... ", "Birds chirp in the distance... "],
        "emphasis": ["The wind whispers through the trees... "]
    },
    "🏰 Medieval Fantasy": {
        "description": "Castles, swords, magic",
        "transitions": ["A trumpet sounds in the distance... ", "The castle gates creak open... ", "Magic crackles in the air... "],
        "emphasis": ["The wizard's staff glows brightly... "]
    },
    "🌌 Sci-Fi": {
        "description": "Space, technology, future",
        "transitions": ["The ship hums steadily... ", "Holographic displays flicker... ", "The space station rotates slowly... "],
        "emphasis": ["Warning: Temporal anomaly detected... "]
    },
    "🎭 Dramatic": {
        "description": "Suspense, tension, reveals",
        "transitions": ["A tense silence falls... ", "The plot thickens... ", "Dramatic music swells... "],
        "emphasis": ["Suddenly... "]
    },
    "🕯️ Mysterious": {
        "description": "Whispers, secrets, dark",
        "transitions": ["A shadow moves in the corner... ", "Whispers echo through the hallway... ", "The candle flickers ominously... "],
        "emphasis": ["A haunting melody drifts through the air... "]
    }
}

# ========== TEXT EXTRACTION ==========
def extract_text_from_pdf(uploaded_file):
    text = ""
    try:
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        for page in pdf_reader.pages:
            try:
                page_text = page.extract_text()
                if page_text:
                    text += page_text.strip() + " "
            except:
                continue
    except Exception as e:
        st.error(f"PDF Error: {str(e)}")
        return None
    
    text = re.sub(r'\s+', ' ', text).strip()
    if len(text) < 10:
        st.warning("⚠️ Could not extract text. PDF may be scanned.")
        return None
    return text

def extract_text_from_docx(uploaded_file):
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
    try:
        text = uploaded_file.getvalue().decode('utf-8', errors='ignore')
        return text.strip()
    except:
        return None

def extract_text(uploaded_file):
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

# ========== STORYTELLING TEXT PROCESSING ==========
def enhance_text_for_storytelling(text, story_style, sound_effect, voice_speed="slow"):
    """Transform plain text into a storytelling experience"""
    
    style_config = STORY_STYLES.get(story_style, STORY_STYLES["📖 Classic Storytelling"])
    effect_config = SOUND_EFFECTS.get(sound_effect, SOUND_EFFECTS["None"])
    
    # Clean text
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Split into sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    # Add storytelling elements
    enhanced_sentences = []
    
    # Add intro
    enhanced_sentences.append(style_config["intro"])
    
    # Process sentences with effects
    effect_counter = 0
    for i, sentence in enumerate(sentences):
        if not sentence.strip():
            continue
            
        # Add sound effect transitions periodically
        if effect_config["transitions"] and i % 3 == 0 and i > 0:
            effect_text = effect_config["transitions"][effect_counter % len(effect_config["transitions"])]
            enhanced_sentences.append(effect_text)
            effect_counter += 1
        
        # Add emphasis for important sentences (long sentences or with "!" or "?")
        if len(sentence) > 80 or '!' in sentence or '?' in sentence:
            if effect_config["emphasis"]:
                emphasis = effect_config["emphasis"][effect_counter % len(effect_config["emphasis"])]
                enhanced_sentences.append(emphasis)
        
        # Add pacing pauses
        if style_config["pause"] and i % 2 == 0:
            sentence = sentence + style_config["pause"]
        
        enhanced_sentences.append(sentence)
    
    # Add conclusion
    enhanced_sentences.append("The end...")
    
    # Join everything
    enhanced_text = " ".join(enhanced_sentences)
    
    # Add speed instructions (these are text hints for TTS)
    if voice_speed == "slow":
        enhanced_text = re.sub(r'\. ', '. . . ', enhanced_text)
        enhanced_text = re.sub(r', ', ', , , ', enhanced_text)
    
    return enhanced_text

# ========== TEXT TO SPEECH WITH SLOWER VOICE ==========
async def text_to_speech_with_speed(text, voice, output_file, speed="slow"):
    """Convert text to speech with adjustable speed"""
    
    # Clean text
    text = re.sub(r'[^\w\s.,!?-]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    
    if not text or len(text) < 5:
        text = "This text could not be processed."
    
    # Truncate if needed
    if len(text) > 4000:
        text = text[:4000]
    
    try:
        # Use edge-tts with rate adjustment
        # Edge TTS supports rate via SSML
        ssml = f"""
        <speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">
            <voice name="{voice}">
                <prosody rate="{speed}" pitch="+0%">
                    {text}
                </prosody>
            </voice>
        </speak>
        """
        
        communicate = edge_tts.Communicate(ssml, voice="en-US-AriaNeural")
        await communicate.save(output_file)
        
        if os.path.exists(output_file) and os.path.getsize(output_file) > 1000:
            return True
        return False
        
    except Exception as e:
        st.warning(f"TTS Error: {str(e)}")
        return False

# ========== WRAPPER ==========
def text_to_speech(text, voice, output_file, speed="slow"):
    """Wrapper for async TTS"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            text_to_speech_with_speed(text, voice, output_file, speed)
        )
        loop.close()
        return result
    except Exception as e:
        st.error(f"Speech error: {str(e)}")
        return False

# ========== AUDIO HELPERS ==========
def get_audio_html(audio_path):
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

# Description
with st.expander("🎯 How It Works", expanded=True):
    st.markdown("""
    1. **Upload** a PDF, DOCX, or TXT file
    2. **Choose a voice** - Storyteller, Narrator, or Dramatic
    3. **Select a storytelling style** - Classic, Dramatic, Fantasy, etc.
    4. **Pick sound effects** - Nature, Medieval, Sci-Fi, etc.
    5. **Adjust speed** - Slow for immersive listening
    6. **Click Convert** and enjoy your custom audiobook!
    """)

uploaded_files = st.file_uploader(
    "📤 Upload your files", 
    type=['pdf', 'docx', 'txt'], 
    accept_multiple_files=True
)

# Settings
col1, col2 = st.columns(2)

with col1:
    voice = st.selectbox(
        "🎤 Choose Voice", 
        list(VOICE_OPTIONS.keys()),
        help="Select a voice that matches your story's tone"
    )
    
    story_style = st.selectbox(
        "📖 Storytelling Style",
        list(STORY_STYLES.keys()),
        help="Choose how your story should be narrated"
    )

with col2:
    sound_effect = st.selectbox(
        "🎵 Sound Effects",
        list(SOUND_EFFECTS.keys()),
        help="Add ambient sounds and transitions"
    )
    
    speed = st.select_slider(
        "⏱️ Speech Speed",
        options=["slower", "slow", "normal", "fast"],
        value="slow",
        help="Slower speeds give a more storytelling feel"
    )

# Speed mapping for SSML
speed_map = {
    "slower": "x-slow",
    "slow": "slow",
    "normal": "medium",
    "fast": "fast"
}

process_btn = st.button("🎬 Create Audiobook", type="primary", use_container_width=True)

if uploaded_files and process_btn:
    voice_code = VOICE_OPTIONS[voice]
    
    with st.spinner("📖 Creating your storytelling audiobook..."):
        all_audio_files = []
        
        for file in uploaded_files:
            st.subheader(f"🎧 {file.name}")
            
            # Extract text
            text = extract_text(file)
            if not text:
                st.warning(f"Skipping {file.name} - no readable text")
                continue
            
            # Show original preview
            with st.expander("📄 Original Text Preview"):
                st.text(text[:500] + "..." if len(text) > 500 else text)
            
            # Enhance text for storytelling
            enhanced_text = enhance_text_for_storytelling(
                text, 
                story_style, 
                sound_effect,
                speed
            )
            
            # Show enhanced preview
            with st.expander("✨ Storytelling Enhanced Preview"):
                st.text(enhanced_text[:500] + "..." if len(enhanced_text) > 500 else enhanced_text)
                st.caption(f"Original: {len(text)} chars → Enhanced: {len(enhanced_text)} chars")
            
            # Process in chunks
            words = enhanced_text.split()
            chunks = []
            for i in range(0, len(words), 500):
                chunks.append(" ".join(words[i:i+500]))
            
            st.info(f"📖 Processing {len(chunks)} chunks with {sound_effect} effects...")
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            audio_files = []
            total_chunks = len(chunks)
            
            for i, chunk in enumerate(chunks):
                status_text.text(f"🎙️ Narrating chunk {i+1}/{total_chunks}...")
                output_file = f"chunk_{i+1}_{file.name.replace(' ', '_')}.mp3"
                
                speed_value = speed_map.get(speed, "slow")
                success = text_to_speech(chunk, voice_code, output_file, speed_value)
                
                if success:
                    audio_files.append(output_file)
                else:
                    status_text.text(f"⚠️ Chunk {i+1} failed, continuing...")
                
                progress_bar.progress((i + 1) / total_chunks)
            
            if not audio_files:
                st.error("❌ Could not generate audio")
                continue
            
            # Create final audio
            if len(audio_files) > 1:
                final_file = f"story_{file.name.replace(' ', '_')}.mp3"
                merged = merge_audio_files(audio_files, final_file)
                final_file = merged if merged else audio_files[0]
            else:
                final_file = audio_files[0]
            
            if final_file and os.path.exists(final_file):
                all_audio_files.append(final_file)
                
                # Play and download
                st.success("✅ Storytelling audiobook ready!")
                st.markdown(get_audio_html(final_file), unsafe_allow_html=True)
                
                with open(final_file, "rb") as f:
                    st.download_button(
                        label=f"⬇️ Download Story.mp3",
                        data=f,
                        file_name=f"{file.name.replace(' ', '_')}_story.mp3",
                        mime="audio/mp3"
                    )
        
        st.balloons()
        st.success("🎉 All stories have been narrated!")

# ========== FOOTER ==========
st.markdown("---")
st.caption("⚡ Powered by AI storytelling • Free • No limits")

with st.expander("💡 Pro Tips"):
    st.markdown("""
    **For the best experience:**
    - 📖 **Classic Storytelling** + **Nature Effects** = Cozy audiobook
    - 🎭 **Dramatic** + **Dramatic Effects** = Thrilling narration
    - 🧙 **Fantasy** + **Medieval Effects** = Epic adventure
    - 🤖 **Sci-Fi** + **Sci-Fi Effects** = Futuristic story
    
    **Voice Guide:**
    - **Aria** - Best for fairy tales and children's stories
    - **Guy** - Great for dramatic narrations
    - **Sonia** - Perfect for British audiobooks
    - **Davis** - Excellent for character voices
    """)
