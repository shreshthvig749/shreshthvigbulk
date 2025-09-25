import streamlit as st

# --- Password protection ---
PASSWORD = "shreshthvig"

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    password_input = st.text_input("Enter password to access the app:", type="password")
    if password_input == PASSWORD:
        st.session_state.logged_in = True
        st.experimental_rerun()
    else:
        st.warning("Incorrect password!")
        st.stop()


import streamlit as st
from rembg import remove
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from io import BytesIO
import zipfile
import os
import numpy as np
from streamlit_drawable_canvas import st_canvas

# --- Page setup ---
st.set_page_config(page_title="Bulk Background Editor", layout="wide")
st.title("Kanchan Fashion Bulk Editor")

# --- Sidebar controls ---
st.sidebar.header("Background Settings")
bg_color = st.sidebar.color_picker("Choose background color", "#A4A4A4")
bg_image_file = st.sidebar.file_uploader("Upload background image", type=["jpg", "jpeg", "png"])
bg_image = Image.open(bg_image_file).convert("RGBA") if bg_image_file else None

st.sidebar.header("Logo & Text Settings")
logo_size_percent = st.sidebar.slider("Logo size (% of image width)", 10, 50, 20)
font_size_percent = st.sidebar.slider("Font size (% of image height)", 2, 30, 4)

st.sidebar.header("Refine Settings")
brush_size = st.sidebar.slider("Brush size (px)", 5, 100, 20)

# --- Upload images ---
uploaded_files = st.file_uploader("Upload images", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

# --- Text inputs ---
col1, col2 = st.columns(2)
with col1:
    text_input1 = st.text_input("Fabric")
with col2:
    text_input2 = st.text_input("Price")

# --- Logo upload section ---
logo_file = st.file_uploader("Upload your logo (PNG with transparency)", type=["png"])
if logo_file:
    logo = Image.open(logo_file).convert("RGBA")
else:
    try:
        logo = Image.open("images/kfpllogo.png").convert("RGBA")
    except FileNotFoundError:
        st.error("Default logo (kfpllogo.png) not found! Please upload your logo.")
        st.stop()

# --- Helper functions ---
def resize_image(img, max_width=1200):
    """Resize image to fit within max_width while maintaining aspect ratio."""
    if img.width > max_width:
        ratio = max_width / img.width
        return img.resize((max_width, int(img.height * ratio)), Image.LANCZOS)
    return img

def add_shadow(fg, offset=(20, 20), blur_radius=30, shadow_color=(0, 0, 0, 180)):
    """Add drop shadow behind the foreground object."""
    shadow = Image.new("RGBA", fg.size, (0, 0, 0, 0))
    alpha = fg.split()[-1]
    shadow_layer = Image.new("RGBA", fg.size, shadow_color)
    shadow.paste(shadow_layer, offset, mask=alpha)
    shadow = shadow.filter(ImageFilter.GaussianBlur(blur_radius))
    combined = Image.alpha_composite(shadow, fg)
    return combined

# --- Initialize session state ---
if "refine_state" not in st.session_state:
    st.session_state.refine_state = {}
if "processed_images" not in st.session_state:
    st.session_state.processed_images = {}

# --- Main processing loop ---
if uploaded_files:
    for idx, uploaded_file in enumerate(uploaded_files):
        filename = uploaded_file.name
        st.subheader(f"Processing: {filename}")

        # Load input image
        input_image = Image.open(uploaded_file).convert("RGBA")

        # Background removal + processing (only first time)
        if filename not in st.session_state.processed_images:
            img_bytes = BytesIO()
            input_image.save(img_bytes, format="PNG")
            no_bg = Image.open(BytesIO(remove(img_bytes.getvalue()))).convert("RGBA")

            # Add shadow
            no_bg = add_shadow(no_bg)

            # Background (color or image)
            if bg_image:
                bg_resized = bg_image.resize(no_bg.size)
            else:
                rgb = tuple(int(bg_color.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
                bg_resized = Image.new("RGBA", no_bg.size, rgb + (255,))

            # Merge foreground with background
            final_img = Image.alpha_composite(bg_resized, no_bg)

            # --- Add logo ---
            logo_width = int(final_img.width * (logo_size_percent / 100))
            logo_ratio = logo_width / logo.width
            logo_height = int(logo.height * logo_ratio)
            logo_resized = logo.resize((logo_width, logo_height))
            margin = int(final_img.width * 0.02)
            final_img.paste(logo_resized, (margin, margin), logo_resized)

            # --- Add text ---
            draw = ImageDraw.Draw(final_img)
            font_size = int(final_img.height * (font_size_percent / 100))
            try:
                font = ImageFont.truetype("Arial Unicode.ttf", font_size)
            except IOError:
                font = ImageFont.load_default()

            y_margin = int(final_img.height * 0.03)
            y_pos = y_margin
            if text_input1:
                bbox1 = draw.textbbox((0, 0), text_input1, font=font)
                x_pos1 = final_img.width - (bbox1[2] - bbox1[0]) - y_margin
                draw.text((x_pos1, y_pos), text_input1, font=font, fill=(0, 0, 0))
                y_pos += (bbox1[3] - bbox1[1]) + y_margin
            if text_input2:
                bbox2 = draw.textbbox((0, 0), text_input2, font=font)
                x_pos2 = final_img.width - (bbox2[2] - bbox2[0]) - y_margin
                draw.text((x_pos2, y_pos), text_input2, font=font, fill=(0, 0, 0))

            st.session_state.processed_images[filename] = final_img

        # Fetch latest processed image
        final_img = st.session_state.processed_images[filename]

        # Display smaller preview
        st.image(resize_image(final_img, max_width=400), caption=f"Processed Image: {filename}")

        # Init refine state
        if filename not in st.session_state.refine_state:
            st.session_state.refine_state[filename] = False

        # Refine / Close buttons
        col1_btn, col2_btn = st.columns([1, 1])
        with col1_btn:
            if st.button(f"Refine {filename}", key=f"refine_btn_{idx}"):
                st.session_state.refine_state[filename] = True
        with col2_btn:
            if st.button(f"Close Refine {filename}", key=f"close_refine_btn_{idx}"):
                st.session_state.refine_state[filename] = False

        # Show refine canvas
        if st.session_state.refine_state[filename]:
            st.write("**Use the brush to restore removed areas:**")

            # Resize canvas for screen
            max_canvas_width = 800
            scale_ratio = min(1, max_canvas_width / final_img.width)
            canvas_width = int(final_img.width * scale_ratio)
            canvas_height = int(final_img.height * scale_ratio)

            canvas_bg = final_img.convert("RGB").resize((canvas_width, canvas_height))

            canvas_result = st_canvas(
                fill_color="rgba(0,0,0,0)",
                stroke_width=brush_size,
                stroke_color="#000000",
                background_image=canvas_bg,
                update_streamlit=True,
                height=canvas_height,
                width=canvas_width,
                drawing_mode="freedraw",
                key=f"canvas_{idx}"
            )

            # Apply edits
            if st.button(f"Apply Edits {filename}", key=f"apply_btn_{idx}"):
                if canvas_result.image_data is not None:
                    canvas_array = canvas_result.image_data.astype("uint8")
                    mask = canvas_array[:, :, 3] > 0

                    # Resize mask to match original image
                    mask_img = Image.fromarray((mask * 255).astype("uint8")).resize(
                        final_img.size, Image.NEAREST
                    )
                    mask = np.array(mask_img) > 0

                    final_array = np.array(st.session_state.processed_images[filename])
                    input_array = np.array(input_image)

                    # Ensure mask fits correctly
                    if mask.shape == final_array.shape[:2]:
                        final_array[mask] = input_array[mask]

                    st.session_state.processed_images[filename] = Image.fromarray(final_array)
                    st.success(f"{filename} edits applied!")
                    st.image(
                        resize_image(st.session_state.processed_images[filename], max_width=400),
                        caption=f"Refined Image: {filename}"
                    )

    # --- ZIP Download ---
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zipf:
        for name, img in st.session_state.processed_images.items():
            img_bytes = BytesIO()
            img.save(img_bytes, format="PNG", quality=100)
            zipf.writestr(os.path.splitext(name)[0] + "_final.png", img_bytes.getvalue())
    zip_buffer.seek(0)

    st.download_button(
        "⬇️ Download All Processed Images as ZIP",
        zip_buffer,
        "processed_images.zip",
        "application/zip"
    )
