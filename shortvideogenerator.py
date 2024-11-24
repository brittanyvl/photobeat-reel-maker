import streamlit as st
from PIL import Image, ImageFilter
import moviepy
from moviepy.editor import ImageClip, concatenate_videoclips, AudioFileClip
import librosa
import numpy as np
import tempfile
import os

# Application Heading
st.title('Photo Beats')
st.header('Vertical Video Made Easy')
st.write("Upload your photos and an audio track and we'll create a vertical video in sync with the beat!")

# Constants
TARGET_WIDTH, TARGET_HEIGHT = 1080, 1920
MAX_IMAGE_DURATION = 2.0  # Max duration for a single image in seconds


def convert_to_9_16(image):
    """
    Converts an image to fit a 9:16 vertical format.

    Args:
        image (PIL.Image.Image): Input image.

    Returns:
        PIL.Image.Image: Processed image with 9:16 aspect ratio.
    """
    img_width, img_height = image.size
    target_aspect_ratio = 9 / 16

    if img_width / img_height < target_aspect_ratio:
        new_height = int(img_width / target_aspect_ratio)
        if img_height < new_height:
            scale_factor = new_height / img_height
            scaled_width = int(img_width * scale_factor)
            scaled_height = int(img_height * scale_factor)
            image = image.resize((scaled_width, scaled_height), Image.LANCZOS)
            img_width, img_height = image.size
        top = (img_height - new_height) // 2
        bottom = top + new_height
        cropped_image = image.crop((0, top, img_width, bottom))
        processed_image = cropped_image
    else:
        background = image.copy()
        background = background.resize((TARGET_WIDTH, TARGET_HEIGHT), Image.LANCZOS)
        background = background.filter(ImageFilter.GaussianBlur(20))
        scale_factor = min(TARGET_WIDTH / img_width, TARGET_HEIGHT / img_height)
        new_width = int(img_width * scale_factor)
        new_height = int(img_height * scale_factor)
        resized_image = image.resize((new_width, new_height), Image.LANCZOS)
        x_offset = (TARGET_WIDTH - new_width) // 2
        y_offset = (TARGET_HEIGHT - new_height) // 2
        background.paste(resized_image, (x_offset, y_offset))
        processed_image = background

    return processed_image


def extract_beats(audio_file_path):
    """
    Extracts beat times and audio duration from an audio file.

    Args:
        audio_file_path (str): Path to the audio file.

    Returns:
        tuple: A tuple containing:
            - beat_times (list): List of times (in seconds) where beats occur.
            - audio_duration (float): Total duration of the audio (in seconds).
    """
    audio_data, sample_rate = librosa.load(audio_file_path, sr=None)
    tempo, beat_frame_indices = librosa.beat.beat_track(y=audio_data, sr=sample_rate)

    if len(beat_frame_indices) == 0:
        # If no beats are detected, fall back to even intervals based on tempo
        beat_interval = 60 / tempo  # Convert BPM to beat duration in seconds
        audio_duration = librosa.get_duration(y=audio_data, sr=sample_rate)
        beat_times = np.arange(0, audio_duration, beat_interval)
    else:
        beat_times = librosa.frames_to_time(beat_frame_indices, sr=sample_rate)

    audio_duration = librosa.get_duration(y=audio_data, sr=sample_rate)
    return beat_times, audio_duration


def generate_video(images, audio_path):
    """
    Generates a vertical video from images and an audio file.

    Args:
        images (list): List of file paths to the images.
        audio_path (str): Path to the audio file.

    Returns:
        VideoClip: A MoviePy VideoClip object with the images synchronized to the audio.
    """
    beat_times, audio_duration = extract_beats(audio_path)

    # Calculate image durations
    image_durations = np.diff(np.append(beat_times, audio_duration))

    # Cap each beat duration to MAX_IMAGE_DURATION, splitting longer beats
    final_durations = []
    for duration in image_durations:
        if duration > MAX_IMAGE_DURATION:
            final_durations.extend([MAX_IMAGE_DURATION] * int(duration // MAX_IMAGE_DURATION))
            remaining = duration % MAX_IMAGE_DURATION
            if remaining > 0:
                final_durations.append(remaining)
        else:
            final_durations.append(duration)

    # Repeat images to match the required number of durations
    images_repeated = images * (len(final_durations) // len(images)) + images[:len(final_durations) % len(images)]

    clips = []
    for i, duration in enumerate(final_durations):
        img = Image.open(images_repeated[i])
        img_9_16 = convert_to_9_16(img)
        img_np = np.array(img_9_16)
        clip = ImageClip(img_np).set_duration(duration)
        clips.append(clip)

    video = concatenate_videoclips(clips, method="compose")
    audio = AudioFileClip(audio_path)
    return video.set_audio(audio).set_duration(audio_duration)


# User uploads
uploaded_images = st.file_uploader("Upload Photos", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
audio_file = st.file_uploader("Upload Audio", type=["mp3", "wav"])

generated_video_path = None

if uploaded_images and audio_file:
    if st.button("Generate Video"):
        with st.spinner("Processing..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio_file:
                temp_audio_file.write(audio_file.read())
                temp_audio_path = temp_audio_file.name

            video = generate_video(uploaded_images, temp_audio_path)

            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_video_file:
                video.write_videofile(temp_video_file.name, fps=24)
                generated_video_path = temp_video_file.name

            st.success("Video generated successfully!")
            os.remove(temp_audio_path)

if generated_video_path:
    st.video(generated_video_path)
    with open(generated_video_path, "rb") as video_file:
        st.download_button(
            "Download Video",
            data=video_file,
            file_name="final_video.mp4",
            mime="video/mp4"
        )
