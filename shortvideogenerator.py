import streamlit as st
import os
from PIL import Image
from moviepy.editor import ImageClip, concatenate_videoclips, AudioFileClip

#Application Heading
st.title('Short Video Generator')
st.write('Upload images and an audio track to create a vertical 9:16 video perfect for IG reels, Meta Shorts, Youtube Shorts, or TikTok.')

#Image Aspect Ratio Conversion:  Crop vertical to size, pad horizontal to size
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

#Interface to upload images and audio
uploaded_images = st.file_uploader("Upload Photos", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
audio_file = st.file_uploader("Upload Audio", type=["mp3", "wav"])

#Process Images & Audio
if uploaded_images and audio_file:
    if not os.path.exists("temp"):
        os.mkdir("temp")

    clips = []
    for image_file in uploaded_images:
        img = Image.open(image_file)
        img_9_16 = convert_to_9_16(img)
        output_path = os.path.join("temp", image_file.name)
        img_9_16.save(output_path)

        clip = ImageClip(output_path).set_duration(3)
        clips.append(clip)

    video = concatenate_videoclips(clips, method="compose")

    with open("temp/audio_temp.mp3", "wb") as audio_out:
        audio_out.write(audio_file.read())
    audio = AudioFileClip("temp/audio_temp.mp3")
    audio_duration = audio.duration

    final_video = video.set_audio(audio).set_duration(audio_duration)

    final_output = "finishedreel.mp4"
    final_video.write_videofile(final_output, fps=24)

    with open(final_output, "rb") as video_file:
        st.download_button(label="Download Your Video", data=video_file, file_name=final_output, mime="video/mp4")

    st.video(final_output)

else:
    st.write("Please upload both images and an audio file to continue.")