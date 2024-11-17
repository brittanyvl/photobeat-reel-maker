import streamlit as st
from PIL import Image, ImageFilter
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
        # Image is taller or not tall enough: crop or scale to 9:16
        new_height = int(img_width / target_aspect_ratio)
        if img_height < new_height:
            # Scale up the image if it's not tall enough
            scale_factor = new_height / img_height
            scaled_width = int(img_width * scale_factor)
            scaled_height = int(img_height * scale_factor)
            image = image.resize((scaled_width, scaled_height), Image.LANCZOS)
            img_width, img_height = image.size  # Update dimensions after scaling
        # Crop to center vertically to match 9:16
        top = (img_height - new_height) // 2
        bottom = top + new_height
        cropped_image = image.crop((0, top, img_width, bottom))
        processed_image = cropped_image
    else:
        # Image is too wide or square: add blurry bars to fit 9:16
        background = image.copy()
        background = background.resize((TARGET_WIDTH, TARGET_HEIGHT), Image.LANCZOS)
        background = background.filter(ImageFilter.GaussianBlur(20))  # Apply a blur effect

        # Resize the original image to fit within the 9:16 area while preserving its aspect ratio
        scale_factor = min(TARGET_WIDTH / img_width, TARGET_HEIGHT / img_height)
        new_width = int(img_width * scale_factor)
        new_height = int(img_height * scale_factor)
        resized_image = image.resize((new_width, new_height), Image.LANCZOS)

        # Center the resized image on the blurred background
        x_offset = (TARGET_WIDTH - new_width) // 2
        y_offset = (TARGET_HEIGHT - new_height) // 2
        background.paste(resized_image, (x_offset, y_offset))
        processed_image = background

    return processed_image

# Audio processing
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
    # Load the audio file using Librosa.
    # `audio_data` contains the audio signal as a NumPy array.
    # `sample_rate` is the sampling rate of the audio (number of samples per second).
    audio_data, sample_rate = librosa.load(audio_file_path, sr=None)

    # Detect the beats in the audio file.
    # `beat_track` identifies beats and returns the tempo and indices of beat frames.
    _, beat_frame_indices = librosa.beat.beat_track(y=audio_data, sr=sample_rate)

    # Convert the beat frame indices to time (in seconds).
    # This step maps the detected beats to their corresponding times in the audio.
    beat_times = librosa.frames_to_time(beat_frame_indices, sr=sample_rate)

    # Calculate the total duration of the audio file in seconds.
    # This is used for aligning visual content or checking the length of the audio if needed later.
    audio_duration = librosa.get_duration(y=audio_data, sr=sample_rate)

    # Return the detected beat times and the total audio duration.
    return beat_times, audio_duration

# Main processing pipeline
def generate_video(images, audio_path):
    """
    Generates a vertical video from images and an audio file.

    Args:
        images (list): List of file paths to the images.
        audio_path (str): Path to the audio file.

    Returns:
        VideoClip: A MoviePy VideoClip object with the images synchronized to the audio.
    """
    # Step 1: Extract beat times and audio duration from the audio file.
    # - `beat_times`: A list of times (in seconds) where beats occur in the audio.
    # - `audio_duration`: The total duration of the audio file (in seconds).
    beat_times, audio_duration = extract_beats(audio_path)

    # Step 2: Calculate image durations based on beat intervals.
    # - `np.diff`: Computes differences between consecutive beat times.
    # - `np.append`: Appends the audio duration to the beat_times list so the last image
    #   covers the final interval to the end of the audio.
    image_durations = np.diff(np.append(beat_times, audio_duration))

    # Step 3: Initialize an empty list to hold individual image clips.
    clips = []

    # Step 4: Loop through each beat interval and create a corresponding image clip.
    for i, duration in enumerate(image_durations):
        # Load the image from the list, cycling through if there are fewer images than beats.
        img = Image.open(images[i % len(images)])

        # Convert the image to fit the 9:16 vertical video format.
        img_9_16 = convert_to_9_16(img)

        # Convert the processed image (PIL Image) to a NumPy array for MoviePy compatibility.
        img_np = np.array(img_9_16)

        # Create a MoviePy ImageClip with the specified duration.
        clip = ImageClip(img_np).set_duration(duration)

        # Append the clip to the list of clips.
        clips.append(clip)

    # Step 5: Concatenate all the image clips into a single video.
    # - `method="compose"` ensures that all clips are aligned properly, especially if
    #   their resolutions or durations differ slightly.
    video = concatenate_videoclips(clips, method="compose")

    # Step 6: Load the audio file using MoviePy's AudioFileClip.
    audio = AudioFileClip(audio_path)

    # Step 7: Set the audio track and duration for the video.
    # - Adds the extracted audio to the video and ensures the video's duration matches
    #   the audio's duration for proper synchronization.
    return video.set_audio(audio).set_duration(audio_duration)


# User uploads
uploaded_images = st.file_uploader("Upload Photos", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
audio_file = st.file_uploader("Upload Audio", type=["mp3", "wav"])

# Placeholder for generated video
generated_video_path = None

# Submit button
if uploaded_images and audio_file:
    if st.button("Generate Video"):
        with st.spinner("Processing..."):
            # Create a temporary file for the audio
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio_file:
                temp_audio_file.write(audio_file.read())
                temp_audio_path = temp_audio_file.name

            # Generate the video
            video = generate_video(uploaded_images, temp_audio_path)

            # Save the video to a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_video_file:
                video.write_videofile(temp_video_file.name, fps=24)
                generated_video_path = temp_video_file.name  # Save the path for reuse

            # Display success message
            st.success("Video generated successfully!")

            # Cleanup temporary audio file
            os.remove(temp_audio_path)

# If a video has been generated, offer a preview and download option
if generated_video_path:
    st.video(generated_video_path)  # Playback the video
    with open(generated_video_path, "rb") as video_file:
        st.download_button(
            "Download Video",
            data=video_file,
            file_name="final_video.mp4",
            mime="video/mp4"
        )

