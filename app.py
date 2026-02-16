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
                
                # Use Gemini 1.5 Flash (fast and supports PDFs)
                model = genai.GenerativeModel("models/gemini-1.5-flash")
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
    
    # Custom HTML/JavaScript for Play, Pause, Resume with voice selection
    # This uses the browser's native Speech Synthesis API
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
        
        <div>
            <button onclick="playTTS()" style="padding: 10px 20px; cursor: pointer; margin-right: 5px;">▶️ Play</button>
            <button onclick="pauseTTS()" style="padding: 10px 20px; cursor: pointer; margin-right: 5px;">⏸️ Pause</button>
            <button onclick="resumeTTS()" style="padding: 10px 20px; cursor: pointer; margin-right: 5px;">▶️ Resume</button>
            <button onclick="stopTTS()" style="padding: 10px 20px; cursor: pointer;">⏹️ Stop</button>
        </div>
    </div>

    <script>
        var msg = new SpeechSynthesisUtterance();
        msg.text = `{text.replace('`', "'").replace('$', '\\$')}`;
        msg.rate = 1.0;
        var voices = [];

        // Load available voices
        function loadVoices() {{
            voices = window.speechSynthesis.getVoices();
            var voiceSelect = document.getElementById('voiceSelect');
            voiceSelect.innerHTML = '';
            
            // Filter for English voices and prioritize Google/Microsoft voices
            var englishVoices = voices.filter(voice => voice.lang.startsWith('en'));
            
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
                premiumVoices.forEach((voice, index) => {{
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
                otherVoices.forEach((voice, index) => {{
                    var option = document.createElement('option');
                    option.value = voices.indexOf(voice);
                    option.textContent = voice.name + ' (' + voice.lang + ')';
                    optgroup.appendChild(option);
                }});
                voiceSelect.appendChild(optgroup);
            }}
            
            // Select a good default voice (prefer Google US English)
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
        loadVoices();

        // Update rate display
        document.getElementById('rateSlider').addEventListener('input', function() {{
            document.getElementById('rateValue').textContent = this.value + 'x';
        }});

        function playTTS() {{
            window.speechSynthesis.cancel(); // Reset any existing speech
            
            // Set selected voice
            var voiceSelect = document.getElementById('voiceSelect');
            var selectedVoiceIndex = voiceSelect.value;
            if (voices[selectedVoiceIndex]) {{
                msg.voice = voices[selectedVoiceIndex];
            }}
            
            // Set rate
            msg.rate = parseFloat(document.getElementById('rateSlider').value);
            
            window.speechSynthesis.speak(msg);
        }}

        function pauseTTS() {{
            window.speechSynthesis.pause();
        }}

        function resumeTTS() {{
            window.speechSynthesis.resume();
        }}

        function stopTTS() {{
            window.speechSynthesis.cancel();
        }}
    </script>
    """
    st.components.v1.html(tts_html, height=200)

    with st.expander("View Extracted Text"):
        st.write(text)
