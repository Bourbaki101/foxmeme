"""One-time official model download. Runtime never accesses the network."""
import hashlib
import json
import io
import zipfile
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://storage.googleapis.com/mediapipe-models"
MODELS = {
    "hand_landmarker": f"{BASE}/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task",
    "face_landmarker": f"{BASE}/face_landmarker/face_landmarker/float16/1/face_landmarker.task",
}


def main():
    directory = ROOT / "assets/models"
    directory.mkdir(parents=True, exist_ok=True)
    manifest_path = directory / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    for name, url in MODELS.items():
        path = directory / (name + ".task")
        expected = manifest.get(name, {}).get("sha256")
        if path.exists() and expected and hashlib.sha256(path.read_bytes()).hexdigest() == expected:
            print(f"Verified {path.name}")
            continue
        print(f"Downloading {url}")
        with urlopen(url, timeout=120) as response:
            data = response.read()
        digest = hashlib.sha256(data).hexdigest()
        if len(data) < 100_000 or not zipfile.is_zipfile(io.BytesIO(data)):
            raise RuntimeError(f"Invalid model archive: {name}")
        if expected and digest != expected:
            raise RuntimeError(f"Checksum mismatch: {name}")
        temp = path.with_suffix(".download")
        temp.write_bytes(data)
        temp.replace(path)
        manifest[name] = dict(url=url, sha256=digest, bytes=len(data))
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
        print(f"Saved {path.name}: {len(data):,} bytes; SHA256 {digest}")


if __name__ == "__main__":
    main()
