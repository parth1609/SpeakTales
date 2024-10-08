import streamlit as st
import os
import requests
from PIL import Image
import io
from io import BytesIO
import urllib.parse
import random
from gtts import gTTS
import base64
import google.generativeai as genai

# Configure Gemini API
GEMINI_API_KEY = st.secrets['GEMINI_API_KEY']
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable is not set")

genai.configure(api_key=GEMINI_API_KEY)

# Cache directory for temporary files
CACHE_DIR = ".cache"
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)


def generate_story(prompt, num_scenes):
    """Generate a short story based on the theme."""
    try:
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(
            f"Write a short story based on the theme: '{prompt}'. "
            f"The story should be divided into {num_scenes} scenes. "
            "Each scene should be a paragraph long. "
            "Do not include 'Scene 1:', 'Scene 2:', etc. in the text.")
        return response.text
    except Exception as e:
        st.error(f"Error generating story: {str(e)}")
        return None


def split_into_scenes(story, num_scenes):
    """Split the story into scenes."""
    if not story:
        return []
    scenes = [scene.strip() for scene in story.split('\n\n') if scene.strip()]
    return scenes[:num_scenes]


@st.cache_data
def generate_image(scene_description):
    """Generate an image based on the scene description."""
    try:
        prompt = urllib.parse.quote(f"{scene_description}, digital art style")
        width = 512
        height = 512
        seed = random.randint(1, 1000)
        model = 'flux'
        image_url = f"https://pollinations.ai/p/{prompt}?width={width}&height={height}&seed={seed}&model={model}"

        response = requests.get(image_url, timeout=15)
        response.raise_for_status()

        image = Image.open(io.BytesIO(response.content))
        return image
    except Exception as e:
        st.error(f"Error generating image: {str(e)}")
        return None


def save_audio_to_file(text, lang='en', accent='com'):
    """Save audio to a temporary file and return the path."""
    try:
        # Create a unique filename
        filename = f"audio_{random.randint(1000, 9999)}.mp3"
        filepath = os.path.join(CACHE_DIR, filename)

        # Generate and save audio
        tts = gTTS(text=text, lang=lang, tld=accent, slow=False)
        tts.save(filepath)

        # Read the file and encode it
        with open(filepath, 'rb') as f:
            audio_bytes = f.read()

        # Clean up the file
        try:
            os.remove(filepath)
        except:
            pass

        return base64.b64encode(audio_bytes).decode()
    except Exception as e:
        st.error(f"Error saving audio: {str(e)}")
        return None


def create_scene_container(scene_num, scene, accent):
    """Create a container for a single scene."""
    st.subheader(f"Scene {scene_num}")

    col1, col2 = st.columns([2, 1])

    with col1:
        image = generate_image(scene)
        if image:
            st.image(image, use_column_width=True)
        else:
            st.error("Unable to generate image for this scene.")

    with col2:
        if scene and scene.strip():
            st.write(scene)
            audio_base64 = save_audio_to_file(scene, accent=accent)
            if audio_base64:
                st.markdown(f"""
                    <audio controls>
                        <source src="data:audio/mp3;base64,{audio_base64}" type="audio/mp3">
                        Your browser does not support the audio element.
                    </audio>
                    """,
                            unsafe_allow_html=True)
            else:
                st.warning("Audio narration unavailable for this scene.")
        else:
            st.warning("This scene has no content.")

    st.markdown("---")


def display_all_scenes(scenes, selected_accent):
    """Display all scenes at once."""
    if not scenes:
        st.warning("No scenes to display")
        return

    accent_map = {
        'US': 'com',
        'UK': 'co.uk',
        'Australia': 'com.au',
        'India': 'co.in',
        'Canada': 'ca'
    }

    accent = accent_map.get(selected_accent, 'com')

    # Create containers for all scenes at once
    for i, scene in enumerate(scenes, 1):
        create_scene_container(i, scene, accent)


def main():
    st.set_page_config(page_title="SpeakTales",
                       page_icon="ðŸ“š",
                       layout="wide")

    st.markdown("""
        <style>
        audio {
            width: 100%;
            margin-top: 10px;
        }
        .stButton>button {
            width: 100%;
        }
        </style>
    """,
                unsafe_allow_html=True)

    st.title("SpeakTales")
    st.markdown("""
    Welcome to AI Storyteller! This app generates a unique story based on your prompt,
    creates images for each scene, and narrates the story to you.
    """)

    st.markdown("""
    **How it works:**
    1. Enter a theme or topic for your story
    2. Choose the number of scenes you want
    3. Select a narration accent
    4. Click "Generate Story" to create your unique AI-generated tale!
    """)

    user_prompt = st.text_input(
        "Enter a theme or topic for your story:",
        placeholder="e.g., 'A space adventure' or 'A day in the life of a cat'"
    ).strip()

    num_scenes = st.slider("Select number of scenes:", 3, 10, 5)

    accent_options = {
        'US': 'com',
        'UK': 'co.uk',
        'Australia': 'com.au',
        'India': 'co.in',
        'Canada': 'ca'
    }
    selected_accent = st.selectbox("Choose narration accent:",
                                   list(accent_options.keys()))

    if st.button("Generate Story", key="generate_story"):
        if not user_prompt:
            st.warning("Please enter a theme or topic for your story.")
            return

        try:
            with st.spinner(
                    "Generating your story... This may take a moment."):
                story = generate_story(user_prompt, num_scenes)
                if not story:
                    st.error("Failed to generate story. Please try again.")
                    return

                scenes = split_into_scenes(story, num_scenes)
                if not scenes:
                    st.warning(
                        "No valid scenes were generated. Please try again with a different prompt."
                    )
                    return

                st.success("Story generated successfully!")
                st.markdown("## Your AI-generated Story")
                display_all_scenes(scenes, selected_accent)

        except Exception as e:
            st.error(f"An unexpected error occurred: {str(e)}")
            st.write(
                "Please try again with a different prompt or refresh the page."
            )

    st.markdown("---")


if __name__ == "__main__":
    main()
