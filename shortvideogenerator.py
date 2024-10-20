import streamlit as st
import os
from PIL import Image
from moviepy.editor import ImageClip, concatenate_videoclips, AudioFileClip
import librosa
import numpy as np
from io import BytesIO
import tempfile

# Application Heading
st.title('Photo Beats')
st.header('Vertical Video Made Easy')
st.write("Upload your photos and an audio track and we'll create a vertical video in sync with the beat!")

# Image Aspect Ratio Conversion: Crop vertical to size, pad horizontal to size
def convert_to_9_16(image):
    target_width, target_height = 1080, 1920
    img_width, img_height = image.size
    aspect_ratio = img_width / img_height

    # Check if the image is horizontal (wider than 9:16)
    if aspect_ratio > 9 / 16:
        # Horizontal: pad with black to fit 9:16
        new_width = target_width
        new_height = int(new_width / aspect_ratio)
        resized_image = image.resize((new_width, new_height), Image.LANCZOS)

        # Create a blank black background for padding
        new_image = Image.new("RGB", (target_width, target_height), (0, 0, 0))
        new_image.paste(resized_image, (0, (target_height - new_height) // 2))

    else:
        # Vertical or square: crop to 9:16
        new_height = target_height
        new_width = int(aspect_ratio * new_height)
        resized_image = image.resize((new_width, new_height), Image.LANCZOS)

        # Ensure new_image is assigned (handle edge cases)
        if new_width > target_width:
            # Crop horizontally
            left = (resized_image.width - target_width) // 2
            right = left + target_width
            new_image = resized_image.crop((left, 0, right, target_height))
        else:
            # Handle vertical/square case without horizontal crop (pad height if needed)
            new_image = resized_image.crop((0, 0, new_width, target_height))

    return new_image

# Convert a PIL Image to a NumPy array for use in ImageClip
def pil_image_to_numpy(image):
    return np.array(image)

# Interface to upload images and audio
uploaded_images = st.file_uploader("Upload Photos", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
audio_file = st.file_uploader("Upload Audio", type=["mp3", "wav"])

# Process Images & Audio after the user hits the "Submit" button
if uploaded_images and audio_file:
    # Add a submit button
    submit_button = st.button(label="Generate Video")

    if submit_button:
        # Ensure the progress bar works properly
        my_bar = st.progress(0, text="Starting the video generation process...")

        # Handle audio file as BytesIO and write it to a temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio_file:
            temp_audio_file.write(audio_file.read())
            temp_audio_file_path = temp_audio_file.name

        # Load the audio file with MoviePy
        audio = AudioFileClip(temp_audio_file_path)
        audio_duration = audio.duration

        # Use librosa to extract beats from the audio file (in memory)
        y, sr = librosa.load(temp_audio_file_path, sr=None)
        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
        beat_times = librosa.frames_to_time(beat_frames, sr=sr)

        # Calculate image durations based on the beat intervals
        num_images = len(uploaded_images)
        if len(beat_times) < num_images:
            st.warning("The audio doesn't have enough detected beats to match the number of images. Adjusting beat detection.")
            beat_times = np.linspace(0, librosa.get_duration(y=y, sr=sr), num_images + 1)

        # Calculate the intervals between each beat
        image_durations = np.diff(beat_times)

        clips = []
        current_image_index = 0
        num_beats = len(image_durations)

        # Create video clips from the uploaded images
        for i in range(num_beats):
            # Read the uploaded image using BytesIO
            img = Image.open(uploaded_images[current_image_index])
            img_9_16 = convert_to_9_16(img)

            # Convert the image to a NumPy array for use in ImageClip
            img_np = pil_image_to_numpy(img_9_16)

            # Create a video clip from the image
            clip = ImageClip(img_np).set_duration(image_durations[i])
            clips.append(clip)

            # Cycle through the images
            current_image_index = (current_image_index + 1) % num_images

            # Update the progress bar (e.g., after every image)
            my_bar.progress(int((i / num_beats) * 100))

        # Concatenate all image clips into a single video
        video = concatenate_videoclips(clips, method="compose")

        # Set the video duration equal to the audio duration and add the audio to the video
        final_video = video.set_audio(audio).set_duration(audio_duration)

        # Write the final video to a file (in memory)
        final_output = "finishedreel.mp4"
        final_video.write_videofile(final_output, fps=24)

        # Provide a download link for the final video
        with open(final_output, "rb") as video_file:
            st.download_button(label="Download Your Video", data=video_file, file_name=final_output, mime="video/mp4")

        # Video playback in Streamlit
        st.video(final_output)
