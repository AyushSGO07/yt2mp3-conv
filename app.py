"""YouTube to MP3 (320 kbps) Video Editor's Studio - Web Application.
Built with Streamlit, yt-dlp, and pydub.
"""

import os
import sys
import subprocess
from typing import Optional

# Ensure audioop compatibility for Python 3.13+
try:
    import audioop
except ImportError:
    try:
        import audioop_lts as audioop
        sys.modules["audioop"] = audioop
    except ImportError:
        pass

import streamlit as st
from core.downloader import YouTubeMP3Downloader
from downloader import parse_timestamp, open_folder

# Page configuration
st.set_page_config(
    page_title="YouTube MP3 Downloader (320kbps)",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling for modern video editor aesthetic
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(90deg, #ff4b4b, #ff8f00);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        color: #9e9e9e;
        font-size: 1.05rem;
        margin-bottom: 1.5rem;
    }
    .track-card {
        background: #1e1e24;
        border: 1px solid #2e2e38;
        border-radius: 10px;
        padding: 1.2rem;
        margin-top: 1rem;
        margin-bottom: 1rem;
    }
    .badge-cbr {
        background-color: #ff4b4b;
        color: white;
        padding: 3px 8px;
        border-radius: 4px;
        font-weight: bold;
        font-size: 0.8rem;
    }
    .badge-sample {
        background-color: #2196f3;
        color: white;
        padding: 3px 8px;
        border-radius: 4px;
        font-weight: bold;
        font-size: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)


def format_seconds(seconds: float) -> str:
    """Format seconds into MM:SS."""
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d}"


# Initialize session state
if "downloader" not in st.session_state:
    st.session_state.downloader = YouTubeMP3Downloader(
        output_dir="downloads",
        sample_rate=48000,
        bitrate="320k",
        normalize=True,
    )
if "history" not in st.session_state:
    st.session_state.history = []
if "current_preview" not in st.session_state:
    st.session_state.current_preview = None
if "current_url" not in st.session_state:
    st.session_state.current_url = ""


# Sidebar settings
with st.sidebar:
    st.image("https://img.icons8.com/color/96/youtube-music.png", width=64)
    st.header("⚙️ Audio & Project Settings")

    output_dir = st.text_input(
        "📁 Output Folder",
        value=os.path.abspath("downloads"),
        help="Where MP3 files will be saved on your disk.",
    )
    if os.path.exists(output_dir):
        if st.button("📂 Open Output Folder in Explorer", use_container_width=True):
            open_folder(output_dir)

    st.markdown("---")
    st.subheader("🎚️ Audio Quality (NLE Standard)")

    bitrate_option = st.selectbox(
        "Bitrate",
        options=["320k", "256k", "192k"],
        index=0,
        help="320k CBR provides the highest MP3 quality for video editing."
    )

    sample_rate_option = st.selectbox(
        "Sample Rate",
        options=[48000, 44100],
        index=0,
        format_func=lambda x: f"{x} Hz ({'SMPTE Video Standard - Premiere / DaVinci' if x == 48000 else 'CD Audio Standard'})",
        help="48000 Hz is the broadcast and video editing timeline standard to avoid sample-rate drift.",
    )

    normalize_toggle = st.checkbox(
        "Normalize Peak Volume (-0.5 dBFS)",
        value=True,
        help="Ensures track volume is balanced and prevents audio clipping on your timeline.",
    )

    st.markdown("---")
    st.info(
        "💡 **Pro-Tip for Video Editors**:\n\n"
        "Drag & drop the downloaded MP3 files directly into Adobe Premiere Pro, "
        "DaVinci Resolve, Final Cut Pro, or CapCut. Embedded album art appears in your media pool!"
    )


# Main Content Area
st.markdown('<div class="main-header">YouTube to MP3 Studio (320 kbps)</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">High-fidelity 320 kbps CBR MP3 downloader with 48kHz audio conform, trimming, and ID3 metadata for video editors.</div>',
    unsafe_allow_html=True
)

tabs = st.tabs(["🎵 Single Track / Quick Download", "📋 Batch URL Downloader", "📚 Download History"])

# ----------------- TAB 1: Single Track -----------------
with tabs[0]:
    col_input, col_btn = st.columns([5, 1])
    with col_input:
        yt_url = st.text_input(
            "Paste YouTube URL (Video, YouTube Music, or Shorts):",
            placeholder="https://www.youtube.com/watch?v=...",
            key="input_url"
        )
    with col_btn:
        st.write("")
        st.write("")
        preview_clicked = st.button("🔍 Inspect", use_container_width=True)

    if preview_clicked and yt_url:
        with st.spinner("Fetching track details from YouTube..."):
            try:
                downloader_instance = YouTubeMP3Downloader(
                    output_dir=output_dir,
                    sample_rate=sample_rate_option,
                    bitrate=bitrate_option,
                    normalize=normalize_toggle,
                )
                preview_data = downloader_instance.get_info(yt_url)
                st.session_state.current_preview = preview_data
                st.session_state.current_url = yt_url
            except Exception as e:
                st.error(f"Failed to fetch video details: {e}")
                st.session_state.current_preview = None

    preview = st.session_state.current_preview

    if preview:
        if preview.get("is_playlist"):
            st.warning(f"⚠️ This URL is a playlist containing {preview.get('count')} tracks. Click below to download all.")
            if st.button(f"⬇️ Download All {preview.get('count')} Songs at 320kbps", type="primary"):
                downloader_instance = YouTubeMP3Downloader(
                    output_dir=output_dir,
                    sample_rate=sample_rate_option,
                    bitrate=bitrate_option,
                    normalize=normalize_toggle,
                )
                progress_bar = st.progress(0)
                status_text = st.empty()

                entries = preview.get("entries", [])
                total = len(entries)
                for idx, entry in enumerate(entries, 1):
                    status_text.text(f"Downloading [{idx}/{total}]: {entry.get('title')}")
                    try:
                        res = downloader_instance.download_song(entry["url"])
                        st.session_state.history.append(res)
                    except Exception as err:
                        st.error(f"Error on {entry.get('title')}: {err}")
                    progress_bar.progress(idx / total)

                status_text.success(f"Playlist download complete! Saved to '{output_dir}'.")
        else:
            # Single video card
            st.markdown('<div class="track-card">', unsafe_allow_html=True)
            col_thumb, col_info = st.columns([1, 2])

            with col_thumb:
                if preview.get("thumbnail"):
                    st.image(preview["thumbnail"], use_container_width=True)

            with col_info:
                st.subheader(preview.get("clean_title"))
                st.write(f"**Artist / Channel:** {preview.get('artist')}")
                st.write(f"**Total Duration:** {preview.get('duration_formatted')} ({preview.get('duration')}s)")
                st.markdown(
                    f'<span class="badge-cbr">{bitrate_option.upper()} CBR</span> '
                    f'<span class="badge-sample">{sample_rate_option} Hz Stereo</span>',
                    unsafe_allow_html=True
                )

            st.markdown('</div>', unsafe_allow_html=True)

            # Audio Trimming & Editing Options
            with st.expander("✂️ Audio Trimming & Video Editing Options (Optional)", expanded=False):
                st.caption("Need only a specific intro, chorus, or section for your video? Specify timestamps below:")
                col_t1, col_t2 = st.columns(2)
                with col_t1:
                    start_str = st.text_input("Start Time (e.g. 0:30 or 30)", value="", placeholder="0:00 (Track start)")
                with col_t2:
                    end_str = st.text_input("End Time (e.g. 2:15 or 135)", value="", placeholder="Track end")

                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    fade_in = st.number_input("Fade In (seconds)", min_value=0.0, max_value=10.0, value=0.0, step=0.5)
                with col_f2:
                    fade_out = st.number_input("Fade Out (seconds)", min_value=0.0, max_value=10.0, value=0.0, step=0.5)

                custom_name = st.text_input("Custom Output Filename (Optional)", placeholder="Leave blank to use Artist - Title")

            # Download Trigger
            if st.button("🚀 Download 320kbps MP3", type="primary", use_container_width=True):
                dl_progress = st.progress(0)
                dl_status = st.empty()

                def update_progress(data):
                    percent = data.get("percent", 0)
                    status = data.get("status", "")
                    if status == "extracting_metadata":
                        dl_status.text("📡 Extracting audio stream from YouTube...")
                    elif status == "downloading":
                        dl_status.text(f"⬇️ Downloading best stream... {percent:.1f}%")
                    elif status == "processing_audio":
                        dl_status.text("🎛️ Processing with pydub (320kbps CBR, 48kHz conform)...")
                    elif status == "embedding_metadata":
                        dl_status.text("🏷️ Embedding ID3 metadata & album cover art...")
                    elif status == "completed":
                        dl_status.text("✅ Finished!")
                    dl_progress.progress(int(percent))

                try:
                    downloader_instance = YouTubeMP3Downloader(
                        output_dir=output_dir,
                        sample_rate=sample_rate_option,
                        bitrate=bitrate_option,
                        normalize=normalize_toggle,
                    )

                    start_sec = parse_timestamp(start_str) if start_str else None
                    end_sec = parse_timestamp(end_str) if end_str else None
                    f_in = fade_in if fade_in > 0 else None
                    f_out = fade_out if fade_out > 0 else None
                    c_name = custom_name.strip() if custom_name.strip() else None

                    result = downloader_instance.download_song(
                        url=st.session_state.current_url,
                        start_sec=start_sec,
                        end_sec=end_sec,
                        fade_in_sec=f_in,
                        fade_out_sec=f_out,
                        custom_filename=c_name,
                        progress_callback=update_progress,
                    )

                    st.session_state.history.append(result)
                    dl_status.success(f"🎉 Saved successfully: **{result['file_name']}** ({result['filesize_mb']} MB)")

                    # Audio Player for immediate preview
                    if os.path.exists(result["file_path"]):
                        with open(result["file_path"], "rb") as audio_file:
                            audio_bytes = audio_file.read()
                        st.audio(audio_bytes, format="audio/mp3")

                        c_left, c_right = st.columns(2)
                        with c_left:
                            st.download_button(
                                label="💾 Save/Download MP3 in Browser",
                                data=audio_bytes,
                                file_name=result["file_name"],
                                mime="audio/mpeg",
                                use_container_width=True
                            )
                        with c_right:
                            if st.button("📂 Reveal in File Explorer", use_container_width=True):
                                open_folder(output_dir)

                except Exception as ex:
                    st.error(f"Download failed: {ex}")


# ----------------- TAB 2: Batch URL Downloader -----------------
with tabs[1]:
    st.subheader("📥 Batch Download Songs for a Video Project")
    st.caption("Paste multiple YouTube URLs (one per line) to download all of them sequentially at 320kbps.")

    batch_text = st.text_area(
        "YouTube URLs (one per line):",
        placeholder="https://www.youtube.com/watch?v=...\nhttps://www.youtube.com/watch?v=...\nhttps://youtu.be/...",
        height=180
    )

    if st.button("🚀 Start Batch Download", type="primary"):
        urls = [line.strip() for line in batch_text.splitlines() if line.strip() and not line.strip().startswith("#")]
        if not urls:
            st.warning("Please enter at least one valid YouTube URL.")
        else:
            b_progress = st.progress(0)
            b_status = st.empty()
            downloader_instance = YouTubeMP3Downloader(
                output_dir=output_dir,
                sample_rate=sample_rate_option,
                bitrate=bitrate_option,
                normalize=normalize_toggle,
            )

            total = len(urls)
            success = 0
            for i, u in enumerate(urls, 1):
                b_status.text(f"Downloading [{i}/{total}]: {u}")
                try:
                    res = downloader_instance.download_song(u)
                    st.session_state.history.append(res)
                    success += 1
                except Exception as be:
                    st.error(f"Failed to download {u}: {be}")
                b_progress.progress(i / total)

            b_status.success(f"Batch completed! Successfully downloaded {success}/{total} tracks.")
            if st.button("📂 Open Output Folder"):
                open_folder(output_dir)


# ----------------- TAB 3: History -----------------
with tabs[2]:
    st.subheader("📜 Download History")
    if not st.session_state.history:
        st.write("No tracks downloaded in this session yet.")
    else:
        for idx, item in enumerate(reversed(st.session_state.history), 1):
            with st.container():
                c1, c2 = st.columns([4, 1])
                with c1:
                    st.markdown(f"**{item.get('title')}** — *{item.get('artist')}*")
                    st.caption(f"File: `{item.get('file_name')}` | Size: {item.get('filesize_mb')} MB | Duration: {item.get('duration_formatted')}")
                    if os.path.exists(item.get("file_path", "")):
                        with open(item["file_path"], "rb") as f:
                            st.audio(f.read(), format="audio/mp3")
                with c2:
                    st.write("")
                    if os.path.exists(item.get("file_path", "")):
                        if st.button(f"📂 Locate", key=f"loc_{idx}"):
                            open_folder(os.path.dirname(item["file_path"]))
                st.markdown("---")
