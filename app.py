import os
import uuid
import subprocess
import re
from flask import Flask, request, jsonify, send_file, render_template, abort

app = Flask(__name__)

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
OUTPUT_FOLDER = os.path.join(os.path.dirname(__file__), "outputs")
MAX_CONTENT_LENGTH = 4 * 1024 * 1024 * 1024  # 4 GB

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

SAFE_FILENAME_RE = re.compile(r"[^\w\-. ]")


def safe_name(name: str) -> str:
    name = name.strip()
    name = SAFE_FILENAME_RE.sub("_", name)
    if not name:
        name = "audio"
    return name


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    if "video" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    video = request.files["video"]
    if not video.filename:
        return jsonify({"error": "Empty filename"}), 400

    job_id = str(uuid.uuid4())
    ext = os.path.splitext(video.filename)[1] or ".mp4"
    input_path = os.path.join(UPLOAD_FOLDER, f"{job_id}{ext}")
    output_path = os.path.join(OUTPUT_FOLDER, f"{job_id}.m4a")

    video.save(input_path)

    # Try copying the audio stream directly (no re-encoding = lossless).
    # Fall back to high-quality AAC if the codec isn't M4A-compatible.
    result = subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", input_path,
            "-vn",            # drop video
            "-c:a", "copy",   # copy audio stream as-is
            output_path,
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        # Fallback: re-encode to high-quality AAC (320 kbps)
        result = subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", input_path,
                "-vn",
                "-c:a", "aac",
                "-b:a", "320k",
                output_path,
            ],
            capture_output=True,
            text=True,
        )

    os.remove(input_path)

    if result.returncode != 0 or not os.path.exists(output_path):
        return jsonify({"error": "Audio extraction failed", "details": result.stderr}), 500

    return jsonify({"job_id": job_id})


@app.route("/download/<job_id>")
def download(job_id):
    # Validate job_id is a UUID to prevent path traversal
    try:
        uuid.UUID(job_id)
    except ValueError:
        abort(400)

    filename = request.args.get("filename", "audio").strip()
    filename = safe_name(filename)
    if not filename.lower().endswith(".m4a"):
        filename += ".m4a"

    output_path = os.path.join(OUTPUT_FOLDER, f"{job_id}.m4a")
    if not os.path.exists(output_path):
        abort(404)

    return send_file(
        output_path,
        as_attachment=True,
        download_name=filename,
        mimetype="audio/mp4",
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
