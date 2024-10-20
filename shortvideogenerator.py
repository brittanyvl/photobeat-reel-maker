import streamlit as st
import os
from PIL import Image
from moviepy.editor import ImageClip, concatenate_videoclips, AudioFileClip
import librosa
import numpy as np
import time

# Application Heading
st.title('Short Video Generator with Beat Synchronization')
st.write(
    'Upload images and an audio track to create a vertical 9:16 video, synced with the audio beats. Perfect for IG Reels, Meta Shorts, YouTube Shorts, or TikTok.')


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


# Interface to upload images and audio
uploaded_images = st.file_uploader("Upload Photos", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
audio_file = st.file_uploader("Upload Audio", type=["mp3", "wav"])

# Add a submit button
submit = st.button('Submit')

# Process the files once submit is clicked
if submit and uploaded_images and audio_file:
    # Display a progress bar for the entire process
    progress_text = "Operation in progress. Please wait..."
    my_bar = st.progress(0.0, text=progress_text)

    # Step 1: Save the audio file temporarily
    with open("temp/audio_temp.mp3", "wb") as audio_out:
        audio_out.write(audio_file.read())

    # Update progress to 10% after audio is saved
    my_bar.progress(0.1)

    # Step 2: Extract beats using librosa
    y, sr = librosa.load("temp/audio_temp.mp3", sr=None)
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)

    # Update progress to 20% after beat extraction
    my_bar.progress(0.2)

    # Step 3: Read the audio using moviepy to get the duration
    audio = AudioFileClip("temp/audio_temp.mp3")
    audio_duration = audio.duration

    # Step 4: Ensure that we have enough beats for the number of images
    num_images = len(uploaded_images)

    if len(beat_times) < num_images:
        st.warning(
            "The audio doesn't have enough detected beats to match the number of images. Adjusting beat detection.")
        beat_times = np.linspace(0, librosa.get_duration(y=y, sr=sr), num_images + 1)

    # Update progress to 30% after adjusting beat times if needed
    my_bar.progress(0.3)

    # Step 5: Calculate the intervals between each beat
    image_durations = np.diff(beat_times)

    # Step 6: If there are more beats than images, loop through the images
    clips = []
    current_image_index = 0
    num_beats = len(image_durations)

    # Step 7: Process each image, apply beat timings, and create clips
    for i in range(num_beats):
        img = Image.open(uploaded_images[current_image_index])
        img_9_16 = convert_to_9_16(img)
        output_path = os.path.join("temp", f"{i}_{uploaded_images[current_image_index].name}")
        img_9_16.save(output_path)

        # Set each image clip duration based on the beat timings
        clip = ImageClip(output_path).set_duration(image_durations[i])
        clips.append(clip)

        # Cycle through the images
        current_image_index = (current_image_index + 1) % num_images

        # Update the progress bar after processing each image
        # Calculate the percentage based on the number of images processed
        progress_percent = 30 + ((i / num_beats) * 50)  # Progress goes from 30% to 80%
        my_bar.progress(min(1.0, progress_percent / 100))  # Scale to 0.0 to 1.0
        time.sleep(0.05)  # Adjust based on your processing speed

    # Step 8: Concatenate all image clips into a single video
    video = concatenate_videoclips(clips, method="compose")
    my_bar.progress(0.8)

    # Step 9: Set the video duration equal to the audio duration and add the audio to the video
    final_video = video.set_audio(audio).set_duration(audio_duration)

    # Step 10: Write the final video to a file
    final_output = "finishedreel.mp4"
    final_video.write_videofile(final_output, fps=24)
    my_bar.progress(0.9)

    # Step 11: Complete the progress bar after video generation
    my_bar.progress(1.0)
    st.success('Video generation complete!')

    # Step 12: Provide a download link for the final video
    with open(final_output, "rb") as video_file:
        st.download_button(label="Download Your Video", data=video_file, file_name=final_output, mime="video/mp4")

    # Step 13: Video playback in Streamlit
    st.video(final_output)

elif submit:
    st.write("Please upload both images and an audio file to continue.")
