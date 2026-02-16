import streamlit as st
import google.generativeai as genai
import base64

# --- APP CONFIG ---
st.set_page_config(page_title="Gemini PDF Reader", page_icon="📖")
st.title("📖 Gemini PDF Reader")
st.write("Upload a PDF and let Gemini read it out loud for you.")

# --- CONFIGURE API KEY FROM SECRETS ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except Exception as e:
    st.error("API key not configured. Please add GEMINI_API_KEY to your Streamlit secrets.")
    st.stop()

# --- PDF UPLOADER ---
uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")

if uploaded_file:
    if st.button("Extract Text with Gemini"):
        with st.spinner("Gemini is reading the document..."):
            try:
                # Get PDF bytes directly
                pdf_bytes = uploaded_file.getvalue()
                
                # Create a Part object with the PDF data
                pdf_part = {
                    "mime_type": "application/pdf",
                    "data": base64.b64encode(pdf_bytes).decode('utf-8')
                }
                
                # Use Gemini Flash Latest (fast and supports PDFs)
                model = genai.GenerativeModel("gemini-flash-latest")
                response = model.generate_content([
                    "Please extract all the text from this document as a single continuous string. "
                    "Do not add any summaries or extra commentary, just the text content.",
                    pdf_part
                ])
                
                # Store text in session state
                st.session_state.extracted_text = response.text
                st.success("Text extracted successfully!")
                
            except Exception as e:
                st.error(f"Error: {e}")

# --- TEXT-TO-SPEECH CONTROLS ---
if "extracted_text" in st.session_state:
    text = st.session_state.extracted_text
    
    st.subheader("Controls")
    
    # Escape text for JavaScript - handle quotes, backticks, and newlines
    import json
    safe_text = json.dumps(text)
    
    # Custom HTML/JavaScript for Play, Pause, Resume with voice selection
    # This uses the browser's native Speech Synthesis API with chunking for long texts
    tts_html = f"""
    <div style="background: #f0f2f6; padding: 20px; border-radius: 10px;">
        <div style="margin-bottom: 15px;">
            <label for="voiceSelect" style="font-weight: bold; margin-right: 10px;">Voice:</label>
            <select id="voiceSelect" style="padding: 8px; border-radius: 5px; min-width: 250px;">
                <option>Loading voices...</option>
            </select>
        </div>
        
        <div style="margin-bottom: 15px;">
            <label for="rateSlider" style="font-weight: bold; margin-right: 10px;">Speed:</label>
            <input type="range" id="rateSlider" min="0.5" max="2" step="0.1" value="1.0" style="width: 200px;">
            <span id="rateValue" style="margin-left: 10px;">1.0x</span>
        </div>
        
        <div style="margin-bottom: 15px;">
            <button id="playBtn" onclick="playTTS()" style="padding: 10px 20px; cursor: pointer; margin-right: 5px;">▶️ Play</button>
            <button id="pauseBtn" onclick="pauseTTS()" style="padding: 10px 20px; cursor: pointer; margin-right: 5px;" disabled>⏸️ Pause</button>
            <button id="resumeBtn" onclick="resumeTTS()" style="padding: 10px 20px; cursor: pointer; margin-right: 5px;" disabled>▶️ Resume</button>
            <button id="stopBtn" onclick="stopTTS()" style="padding: 10px 20px; cursor: pointer;" disabled>⏹️ Stop</button>
        </div>
        
        <div id="status" style="font-size: 14px; color: #666;"></div>
    </div>

    <script>
        const fullText = {safe_text};
        var voices = [];
        var currentUtterance = null;
        var isPaused = false;
        var isSpeaking = false;
        var textChunks = [];
        var currentChunkIndex = 0;

        // Split text into chunks (Speech API has limits)
        function chunkText(text, maxLength = 200) {{
            const sentences = text.match(/[^.!?]+[.!?]+/g) || [text];
            const chunks = [];
            let currentChunk = '';
            
            for (let sentence of sentences) {{
                if ((currentChunk + sentence).length > maxLength && currentChunk.length > 0) {{
                    chunks.push(currentChunk.trim());
                    currentChunk = sentence;
                }} else {{
                    currentChunk += sentence;
                }}
            }}
            if (currentChunk.trim()) {{
                chunks.push(currentChunk.trim());
            }}
            return chunks;
        }}

        // Load available voices
        function loadVoices() {{
            voices = window.speechSynthesis.getVoices();
            var voiceSelect = document.getElementById('voiceSelect');
            voiceSelect.innerHTML = '';
            
            if (voices.length === 0) {{
                voiceSelect.innerHTML = '<option>Loading voices...</option>';
                return;
            }}
            
            // Filter for English voices
            var englishVoices = voices.filter(voice => voice.lang.startsWith('en'));
            
            if (englishVoices.length === 0) {{
                englishVoices = voices; // Use all if no English found
            }}
            
            // Separate premium voices (Google, Microsoft) from others
            var premiumVoices = englishVoices.filter(voice => 
                voice.name.includes('Google') || 
                voice.name.includes('Microsoft') ||
                voice.name.includes('Premium')
            );
            var otherVoices = englishVoices.filter(voice => 
                !voice.name.includes('Google') && 
                !voice.name.includes('Microsoft') &&
                !voice.name.includes('Premium')
            );
            
            // Add premium voices first
            if (premiumVoices.length > 0) {{
                var optgroup = document.createElement('optgroup');
                optgroup.label = 'Premium Voices';
                premiumVoices.forEach((voice) => {{
                    var option = document.createElement('option');
                    option.value = voices.indexOf(voice);
                    option.textContent = voice.name + ' (' + voice.lang + ')';
                    optgroup.appendChild(option);
                }});
                voiceSelect.appendChild(optgroup);
            }}
            
            // Add other voices
            if (otherVoices.length > 0) {{
                var optgroup = document.createElement('optgroup');
                optgroup.label = 'Other Voices';
                otherVoices.forEach((voice) => {{
                    var option = document.createElement('option');
                    option.value = voices.indexOf(voice);
                    option.textContent = voice.name + ' (' + voice.lang + ')';
                    optgroup.appendChild(option);
                }});
                voiceSelect.appendChild(optgroup);
            }}
            
            // Select a good default voice
            var defaultVoice = voices.findIndex(v => v.name.includes('Google US English'));
            if (defaultVoice === -1) {{
                defaultVoice = voices.findIndex(v => v.name.includes('Google'));
            }}
            if (defaultVoice !== -1) {{
                voiceSelect.value = defaultVoice;
            }}
        }}

        // Load voices when ready
        if (speechSynthesis.onvoiceschanged !== undefined) {{
            speechSynthesis.onvoiceschanged = loadVoices;
        }}
        setTimeout(loadVoices, 100); // Also try loading immediately

        // Update rate display
        document.getElementById('rateSlider').addEventListener('input', function() {{
            document.getElementById('rateValue').textContent = this.value + 'x';
        }});

        function updateButtons(playing, paused) {{
            document.getElementById('playBtn').disabled = playing && !paused;
            document.getElementById('pauseBtn').disabled = !playing || paused;
            document.getElementById('resumeBtn').disabled = !paused;
            document.getElementById('stopBtn').disabled = !playing;
        }}

        function updateStatus(message) {{
            document.getElementById('status').textContent = message;
        }}

        function speakChunk(chunkIndex) {{
            if (chunkIndex >= textChunks.length) {{
                isSpeaking = false;
                updateButtons(false, false);
                updateStatus('Finished reading');
                return;
            }}

            currentChunkIndex = chunkIndex;
            const utterance = new SpeechSynthesisUtterance(textChunks[chunkIndex]);
            
            // Set voice
            var voiceSelect = document.getElementById('voiceSelect');
            var selectedVoiceIndex = voiceSelect.value;
            if (voices[selectedVoiceIndex]) {{
                utterance.voice = voices[selectedVoiceIndex];
            }}
            
            // Set rate
            utterance.rate = parseFloat(document.getElementById('rateSlider').value);
            
            utterance.onend = function() {{
                if (!isPaused && isSpeaking) {{
                    speakChunk(chunkIndex + 1);
                }}
            }};
            
            utterance.onerror = function(event) {{
                console.error('Speech error:', event);
                updateStatus('Error: ' + event.error);
                isSpeaking = false;
                updateButtons(false, false);
            }};
            
            currentUtterance = utterance;
            window.speechSynthesis.speak(utterance);
            updateStatus(`Reading chunk ${{chunkIndex + 1}} of ${{textChunks.length}}...`);
        }}

        function playTTS() {{
            window.speechSynthesis.cancel();
            textChunks = chunkText(fullText);
            currentChunkIndex = 0;
            isPaused = false;
            isSpeaking = true;
            updateButtons(true, false);
            updateStatus('Starting playback...');
            speakChunk(0);
        }}

        function pauseTTS() {{
            if (isSpeaking) {{
                window.speechSynthesis.pause();
                isPaused = true;
                updateButtons(true, true);
                updateStatus('Paused');
            }}
        }}

        function resumeTTS() {{
            if (isPaused) {{
                window.speechSynthesis.resume();
                isPaused = false;
                updateButtons(true, false);
                updateStatus(`Reading chunk ${{currentChunkIndex + 1}} of ${{textChunks.length}}...`);
            }}
        }}

        function stopTTS() {{
            window.speechSynthesis.cancel();
            isSpeaking = false;
            isPaused = false;
            currentChunkIndex = 0;
            updateButtons(false, false);
            updateStatus('Stopped');
        }}
        
        // Initial button state
        updateButtons(false, false);
    </script>
    """
    st.components.v1.html(tts_html, height=250)

    with st.expander("View Extracted Text"):
        st.write(text)
