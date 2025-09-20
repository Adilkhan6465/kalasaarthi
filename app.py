import os
import streamlit as st
import google.generativeai as genai
import qrcode
import io
from PIL import Image
from deep_translator import GoogleTranslator

import io

def _bytes_len(s: str) -> int:
    return len(s.encode("utf-8"))

def generate_qr_image_from_text(text: str, model=None, max_bytes=2500):
    """
    Generate a QR PNG buffer for `text`. If the text is too large for QR,
    attempt to ask the AI model to summarize it (if provided). If summarization
    fails or model isn't available, truncate safely. Returns (buf, final_text).
    """
    if text is None:
        text = ""
    qr_text = text.strip()

    # Safety: small quick path
    if _bytes_len(qr_text) == 0:
        qr_text = "Artisan information not available."

    # If too long in bytes, try to shorten using model (if available)
    attempts = 0
    while _bytes_len(qr_text) > max_bytes and attempts < 3:
        attempts += 1
        if model is None:
            # no model available — truncate
            qr_text = qr_text.encode("utf-8")[:max_bytes].decode("utf-8", errors="ignore")
            break

        # Ask AI to summarize into a short, QR-friendly summary
        # Keep prompt minimal and ask for a concise output
        shorten_prompt = f"""
You are KalaSaarthi. Condense the following artisan and craft information into a short,
customer-friendly summary suitable to embed in a QR code. Keep the essential details,
make it engaging and concise, and limit the output to about {max_bytes//4} characters.
Do not add headings, disclaimers or extra explanation. Only return the short summary.

Text:
{qr_text}
"""
        try:
            resp = model.generate_content(shorten_prompt)
            new_text = resp.text.strip()
            # fallback if model returned an empty answer
            if not new_text:
                qr_text = qr_text.encode("utf-8")[:max_bytes].decode("utf-8", errors="ignore")
                break
            qr_text = new_text
        except Exception:
            # if any error from model, just truncate safely
            qr_text = qr_text.encode("utf-8")[:max_bytes].decode("utf-8", errors="ignore")
            break

    # Final safety truncate if still too long
    if _bytes_len(qr_text) > max_bytes:
        qr_text = qr_text.encode("utf-8")[: max_bytes - 3].decode("utf-8", errors="ignore") + "..."

    # Now try to create QR, but catch ValueError and reduce if needed
    import qrcode
    try:
        img = qrcode.make(qr_text)
    except ValueError:
        # If qrcode still errors, aggressively truncate and retry
        qr_text = qr_text[:1000]
        try:
            img = qrcode.make(qr_text)
        except Exception as e:
            # final fallback: create QR for a simple short message
            fallback = "Artisan info (see product page)"
            img = qrcode.make(fallback)
            qr_text = fallback

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf, qr_text

# ✅ Gemini API key from secrets.toml
GEMINI_KEY = st.secrets["GEMINI_API_KEY"]

genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# Load CSS file
with open("styles/style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.set_page_config(page_title="KalaSaarthi", layout="centered")
st.title("🎨 KalaSaarthi – AI Assistant (Free Version)")

# ✅ Image upload placeholder
st.header("Upload Product Image (Optional)")
photo = st.file_uploader("Choose image", type=["jpg","jpeg","png"])
if photo:
    img_bytes = photo.read()
    img = Image.open(io.BytesIO(img_bytes))
    img.thumbnail((300,300))
    buf = io.BytesIO()
    img.save(buf, format="png")
    buf.seek(0)
    st.image(buf, caption="Uploaded image", use_container_width=False)
    st.info("Image feedback feature is temporarily disabled due to lack of credits. In future version, lighting, sharpness and background suggestions will be provided here.")

# ✅ Story input
st.header("Share Your Story")
typed = st.text_area("Describe your product, craft, or materials here")

st.markdown("<hr>", unsafe_allow_html=True)

final_text = typed.strip()

# ✅ Initialize session state
if "result_json" not in st.session_state:
    st.session_state["result_json"] = {}
if "description_text" not in st.session_state:
    st.session_state["description_text"] = ""
    
# ✅ Additional Inputs for Artisan and Craft Process
st.subheader("Artisan Details")
artisan_input = st.text_area("Enter artisan name, city, experience, etc.")

st.markdown("<hr>", unsafe_allow_html=True)

st.subheader("Craft Process")
process_input = st.text_area("Enter craft process details (Optional)")

st.markdown("<hr>", unsafe_allow_html=True)

# Store inputs in session state
st.session_state["artisan_input"] = artisan_input.strip()
st.session_state["process_input"] = process_input.strip()    

# ✅ Generate button
st.header("Generate Product Details")
if st.button("✨ Generate"):
    if not final_text:
        st.warning("Please write something before generating!")
    else:
        prompt = f"""You are KalaSaarthi, an assistant helping artisans create product details.
Based on this story: {final_text}
Write:
1) Title (<= 60 chars)
2) SEO-friendly description (80–150 words)
3) 8 hashtags (comma separated)
Return JSON like {{ "title": "", "description": "", "hashtags": "" }}.
"""
        with st.spinner("Generating ..."):
            try:
                response = model.generate_content(prompt)
                result_text = response.text
            except Exception as e:
                st.error("Generation error: " + str(e))
                result_text = ""

        import json, re
        try:
            match = re.search(r"\{[\s\S]*\}", result_text)
            result_json = json.loads(match.group(0)) if match else {}
        except:
            result_json = {}

        # Store result in session state
        st.session_state["result_json"] = result_json
        st.session_state["description_text"] = result_json.get("description", "")

# ✅ Display generated details if available
if st.session_state["result_json"]:
    result_json = st.session_state["result_json"]
    st.subheader("Generated Details")
    if result_json.get("title"):
        st.markdown(f"**Title:** {result_json['title']}")
    if result_json.get("description"):
        st.markdown(f"**Description:** {result_json['description']}")
    if result_json.get("hashtags"):
        st.markdown(f"**Hashtags:** {result_json['hashtags']}")

    

    # ✅ Translation section
    st.subheader("Translations")
    desc = st.session_state.get("description_text", "")
    title = st.session_state.get("result_json",{}).get("title", "")
    hashtags = st.session_state.get("result_json",{}).get("hashtags", "")
    
    lang = st.selectbox("Choose target language", ["Hindi", "Nepali", "Marathi", "Kannada"])

    if not desc and not title and not hashtags:
        st.info("Details not available for translation.")
    else:
        if lang:
            try:
                target_code = {
                    "Hindi": "hi",
                    "Nepali": "ne",
                    "Marathi": "mr",
                    "Kannada": "kn"
                }
                code = target_code[lang]
                
                translated_title = GoogleTranslator(source='auto', target=code).translate(title) if title else ""

                translated_desc = GoogleTranslator(source='auto', target=code).translate(desc) if desc else ""
 
                translated_hashtags = GoogleTranslator(source='auto', target=code).translate(hashtags) if hashtags else ""


                #st.subheader("Title (English)")
                #st.write(title)
                
                st.subheader(f"Title ({lang})")
                st.write(translated_title)

                #st.subheader("Description (English)")
                #st.write(desc)

                st.subheader(f"Description ({lang})")
                st.write(translated_desc)

                #st.subheader("Hashtages (English)")
                #st.write(hashtags)

                st.subheader(f"Hashtags ({lang})")
                st.write(translated_hashtags)

            except Exception as e:
                st.info(f"Translation failed: {str(e)}")

    st.markdown("*Other languages:*")
    st.info("More languages will be available in future updates.")

    
 
    # ✅ Trend Mapper Section
    st.subheader("Trend Suggestions")
    product_title = result_json.get("title", "")
    product_description = result_json.get("description", "")

    if not product_title and not product_description:
        st.info("Product details not available to generate trends.")
    else:
        trend_prompt = f"""
        You are an expert market analyst. Based only on the following product details, suggest e-commerce trends clearly and concisely.
        Product Title: "{product_title}"
        Product Description: "{product_description}"
        Please provide the following:
        1. Top regions where this product is in demand.
        2. Trending colors buyers prefer.
        3. Popular styles or design variations in those regions.
        Instructions:
        - Provide only the requested information.
        - Do not include disclaimers, introductions, greetings, or unrelated explanations.
        - Avoid phrases like "These are educated guesses" or similar content.
        - Do not add sources, comments, or any text outside the trend suggestions.
        """

        with st.spinner("Analyzing trends using AI..."):
            try:
                trend_response = model.generate_content(trend_prompt)
                trend_text = trend_response.text.strip()
                st.markdown(trend_text)
            except Exception as e:
                st.error("Trend analysis failed: " + str(e))
                
    
    # -------------------------
    # QR Code (Artisan + Process)
    # -------------------------
    st.subheader("QR Code")

    artisan_text = st.session_state.get("artisan_input", "").strip()
    process_text = st.session_state.get("process_input", "").strip()

    # ✅ Artisan details compulsory
    if not artisan_text:
        st.warning("⚠️ Please provide artisan details to generate QR code.")
    else:
        # Prompt banayenge jo 80–120 words ka ho aur app ka naam bilkul na aaye
        qr_prompt = f"""
        You are KalaSaarthi, but do NOT mention your own name.
        Write only as if the artisan is directly introducing themselves
        and their craft process.

        Requirements:
        - Focus only on artisan introduction + craft process.
        - Do NOT include lines like "I'm KalaSaarthi" or "this QR unlocks".
        - Make it professional, detailed (80–120 words).
        - Customer-friendly storytelling style.
        - If craft process info is not provided, skip it naturally.

        Product Title: "{product_title}"
        Product Description: "{product_description}"
        Artisan Info (must use): "{artisan_text}"
        Craft Process Info: "{process_text if process_text else "Not provided"}"

        Return ONLY the combined plain text (no greetings, no extra notes).
        """

        with st.spinner("Generating artisan & process text for QR..."):
            try:
                response = model.generate_content(qr_prompt)
                raw_text = response.text.strip()

                # ✅ Clean text (remove markdown / quotes if AI adds)
                import re
                match = re.search(r"[A-Za-z].*", raw_text, re.S)
                combined_text = match.group(0).strip() if match else raw_text

                # ✅ Word limit safeguard (max ~120 words for QR capacity)
                words = combined_text.split()
                if len(words) > 120:
                    combined_text = " ".join(words[:120]) + "..."
            except Exception as e:
                st.error("QR text generation failed: " + str(e))
                combined_text = "Artisan and craft process details not available."

        # ✅ Generate QR
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_Q,  # higher capacity than H
            box_size=6,
            border=4,
        )
        qr.add_data(combined_text)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")
  
        # ✅ Convert to Bytes
        buf = io.BytesIO()
        qr_img.save(buf, format="PNG")
        qr_bytes = buf.getvalue()

        # ✅ Show + Download
        st.image(qr_bytes, caption="QR Code (scan to view artisan story)", width=250)
        st.download_button(
            "📥 Download QR Image",
            data=qr_bytes,
            file_name="artisan_process_qr.png",
            mime="image/png"
        )
        st.markdown("<style>.stDownloadButton button {background-color:#FF9800 !important;}</style>", unsafe_allow_html=True)
    