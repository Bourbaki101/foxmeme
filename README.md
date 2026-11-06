# MemeCam

MemeCam is a Windows desktop webcam effects studio. Hand gestures and calibrated facial expressions trigger your images; face landmarks keep them aligned to your face or eyes. Video processing uses local MediaPipe Tasks models. OBS supplies the virtual camera.

**¿Quieres el EXE y un icono en el escritorio?** Sigue [Build and test a Windows executable](#build-and-test-a-windows-executable), desde descargar el repo hasta crear el acceso directo. GitHub contiene el código fuente; debes generar el EXE con esos pasos.

```text
Physical webcam → MemeCam Output → OBS Window Capture
                                      ↓
                              OBS Virtual Camera → Teams / Discord / Zoom / Meet
```

## Requirements and installation

Windows 10/11 x64, Python **3.11 or 3.12** x64, a physical webcam, and OBS Studio for virtual-camera output. Python 3.13+ is excluded because the pinned MediaPipe wheel does not support it. Use a writable source checkout; configuration and assets live beside the source. For an experimental portable Windows executable, see the build steps below.

Run PowerShell in the project directory:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe scripts\create_assets.py
.\.venv\Scripts\python.exe scripts\setup_models.py
.\.venv\Scripts\python.exe -m memecam
```

Installation and the one-time model download need internet. Subsequent launches use local files. The model downloader uses versioned official Google URLs and verifies SHA256 against `assets/models/manifest.json`. Keep that manifest with the project. No camera images are saved or uploaded by MemeCam.

The dependency deliberately pins MediaPipe **0.10.21** while using its Tasks API. During development, the 0.10.35 Windows wheel attempted Clearcut metric uploads; 0.10.21 avoids that observed behavior. Do not upgrade the pin without reviewing runtime network behavior. See the [upstream telemetry report](https://github.com/google-ai-edge/mediapipe/issues/6291) and official [Hand Landmarker](https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker/python) / [Face Landmarker](https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker/python) APIs. The application does not implement a virtual-camera driver, server, cloud API, or recording feature.

For the exact tested Windows/Python 3.12 dependency set, install `requirements-lock.txt` before `pip install -e ".[dev]"`. Only the contrib OpenCV distribution is used; it supplies the normal OpenCV APIs too.

After installation and the model download, start it with:

On Windows, run `powershell -ExecutionPolicy Bypass -File .\scripts\create_shortcut.ps1` to create a **MemeCam** shortcut on the desktop, then double-click it to open the app without a console. This source-mode shortcut uses `.venv\Scripts\pythonw.exe`. Shortcuts are local and are not included in a GitHub download. Keep the project folder and its `.venv` in place; recreate the shortcut after moving the project. For a shortcut that opens the compiled EXE instead, use step 5 below.

```powershell
.\launch.ps1
# If script execution policy prevents running .ps1:
.\.venv\Scripts\python.exe -m memecam
```

## Build and test a Windows executable

This is an **experimental PyInstaller recipe**, not a validated release build or installer. The source application has automated tests; the frozen executable still needs the checks below on the target machine. Build on Windows x64 with Python **3.12 x64**. Internet is needed to install dependencies and download the models; the completed bundle is intended to run offline.

### 1. Download a clean copy

In PowerShell, open a writable folder and run (Git must be installed):

```powershell
git clone https://github.com/Bourbaki101/foxmeme.git
cd foxmeme
```

Alternatively, use **Code → Download ZIP** on GitHub, extract it, and open PowerShell inside the extracted folder containing `pyproject.toml`. Run every subsequent command from that folder. A fresh download contains neither `.venv` nor the `.task` models.

### 2. Install and check the source application

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pip install "pyinstaller>=6,<7"
.\.venv\Scripts\python.exe scripts\create_assets.py
.\.venv\Scripts\python.exe scripts\setup_models.py
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.tmp\pytest
.\.venv\Scripts\python.exe scripts\verify_vision.py
.\.venv\Scripts\python.exe -m memecam --demo --smoke-test
```

Stop and resolve any failed command before continuing. `verify_vision.py` checks real model loading and inference; the demo checks UI startup without using the webcam. The commands above resolve dependencies from `pyproject.toml`; `requirements-lock.txt` records the original development environment and is optional for this recipe.

### 3. Generate the portable folder and EXE

Run this PowerShell command; each backtick must be the last character on its line:

```powershell
.\.venv\Scripts\python.exe -m PyInstaller `
  --noconfirm --clean --onedir --windowed `
  --name MemeCam --icon assets\memecam.ico `
  --contents-directory . `
  --distpath .tmp\dist --workpath .tmp\build --specpath .tmp `
  --paths . `
  --collect-all mediapipe `
  --collect-all cv2_enumerate_cameras `
  --add-data "assets:assets" `
  --add-data "config/overlays.json:config" `
  --add-data "config/gestures.json:config" `
  --add-data "config/settings.example.json:config" `
  memecam\__main__.py
```

The executable is **`.tmp\dist\MemeCam\MemeCam.exe`**. Keep the **entire `MemeCam` folder**, including its DLLs, Qt plugins, `assets` and `config`; copying only the EXE will not work. Build outputs stay under the already ignored `.tmp/` directory. Rebuilding replaces the output folder, so back up any settings or imported images stored there first.

`--contents-directory .` keeps resources beside the EXE, matching the application's existing resource paths. Use this `--onedir` layout: a `--onefile` build would need changes to resource and persistence paths before it can preserve user edits reliably. The flags are documented in the [PyInstaller usage guide](https://pyinstaller.org/en/stable/usage.html).

Build from a clean download: the command includes all of `assets`, including downloaded models and any images you have added there. Only the three listed default configuration files are bundled; local settings and facial calibrations are not copied.

### 4. Test and share

First check the frozen UI from PowerShell, waiting for the process and checking its exit code:

```powershell
$demoProcess = Start-Process -FilePath .\.tmp\dist\MemeCam\MemeCam.exe -ArgumentList '--demo', '--smoke-test' -Wait -PassThru
$demoProcess.ExitCode
```

Expect a synthetic preview to open, close automatically after about two seconds, and return **0**. This does not test camera access or frozen model loading. Then double-click `.tmp\dist\MemeCam\MemeCam.exe` and:

1. Select your physical camera in **Ajustes**, enable hand and face detection, and click **Encender cámara**. Confirm live video and no model/DLL errors.
2. Use **+ Subir mi imagen**, choose a PNG/JPG/WebP, adjust its placement and click **3 · Guardar y usar**. Then try **Guardar y activar con una expresión →**. Hold a thumbs-up gesture and a peace sign to check the built-in effects too.
3. Close and reopen the EXE to confirm settings, imported images, and saved facial gestures persist.
4. Open **Salida OBS ↗** and follow the OBS instructions below if you want to test a virtual camera. Complete `docs/MANUAL_TESTS.md` for a fuller check.
5. Copy the entire `MemeCam` folder to another writable location, outside the checkout, and repeat these checks. Test on a Windows x64 machine without Python before treating the bundle as distributable.

To share it, ZIP the whole `MemeCam` folder. Recipients extract the ZIP into a writable folder and open `MemeCam.exe`; the bundle is intended to include Python and its dependencies. Keep it out of protected locations such as `Program Files`: the app writes `config`, `assets/overlays`, and `logs` beside the EXE. OBS remains a separate installation for virtual-camera use.

If startup fails, inspect `.tmp\dist\MemeCam\logs\memecam.log`. If it fails before logging starts, rebuild with **`--console` instead of `--windowed`**, run the EXE from PowerShell, and inspect the traceback. Check that both `assets/models/hand_landmarker.task` and `assets/models/face_landmarker.task` are in the bundle. For missing runtime DLLs, install the Microsoft Visual C++ x64 runtime. A successful source run alone does not establish that the frozen build works.

### 5. EXE con icono en el escritorio

El comando de compilación ya incorpora `assets/memecam.ico` al EXE. El acceso directo usará ese mismo icono y abrirá MemeCam sin una consola.

Primero copia **toda** la carpeta `.tmp\dist\MemeCam` a una ubicación permanente donde puedas escribir, por ejemplo `C:\Users\TU_USUARIO\Apps\MemeCam`. Puedes hacerlo con el Explorador de archivos. Conserva dentro el EXE, las DLL, `assets` y `config`. Después, desde PowerShell en la carpeta del repo, ejecuta este comando **sustituyendo la ruta por la ubicación real de tu EXE**:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\create_shortcut.ps1 -ExecutablePath "C:\Users\TU_USUARIO\Apps\MemeCam\MemeCam.exe"
```

El script crea **MemeCam.lnk** en tu escritorio de Windows, también si está redirigido a OneDrive. Si ya existe un acceso directo llamado MemeCam, lo actualiza para que abra ese EXE. Haz doble clic en el icono **MemeCam** y prueba **+ Subir mi imagen**. El acceso directo del EXE no depende de la `.venv` del repo.

Para una prueba rápida, puedes apuntar directamente al resultado de la compilación:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\create_shortcut.ps1 -ExecutablePath ".\.tmp\dist\MemeCam\MemeCam.exe"
```

En ese caso debes conservar esa carpeta `.tmp\dist\MemeCam`. Si después mueves la app, vuelve a ejecutar el script con la nueva ruta. Si compartes un ZIP, cada persona debe extraer la carpeta completa y crear su propio acceso directo; los archivos `.lnk` de otra computadora contienen rutas que pueden no existir en la suya.

Sin el script también puedes hacer clic derecho en `MemeCam.exe` → **Mostrar más opciones** → **Enviar a** → **Escritorio (crear acceso directo)**.

## Camera and controls

Open **Ajustes** in the right panel to select a webcam, resolution, and requested FPS, then click **Encender cámara** in the header. **Mi estudio** offers image creation and the hand gesture guide; recognition details and output options are grouped under **Ajustes**. The default is 1280×720 at 30 FPS. Devices can negotiate a different format; the footer displays actual frame dimensions and measured processing FPS. Stop before changing cameras or resolution. Refresh discovers newly connected cameras. Capture tries DirectShow first, then Media Foundation.

Hand detection, face tracking, mirroring, and preview debug can be changed live. Debug draws hand connections, face landmark points, candidate, confirmation progress, last confirmed gesture, and measured FPS. The Settings detection section shows the candidate and progress even when debug is off. With both detectors disabled, camera and manual library triggers still work.

| Gesture | Action |
| --- | --- |
| Peace: index/middle straight, ring/pinky folded | Toggle persistent eye-tracked glasses |
| Thumbs up, other fingers folded | Approved for 2 seconds |
| Thumbs down, other fingers folded | Rejected for 2 seconds |
| Open palm, fingers and thumb extended | BRUH reaction for 2 seconds |
| Fist, all fingers folded | Clear all active overlays |

Hold a gesture for 350 ms. A confirmed gesture latches: holding it does not repeatedly trigger. The gesture must disappear or change for at least 250 ms to rearm, and all triggers have an 800 ms global cooldown. Keep one hand fully visible, approximately facing the camera, with good lighting. Sideways thumbs and ambiguous finger configurations are deliberately rejected. Classification uses metric hand-world joint geometry; thumb direction is intentionally relative to the upright camera image. The MVP tracks one hand and one face.

Settings persist in `config/settings.json` on changes, camera start, and close. Missing settings use defaults; invalid settings produce a visible warning and fall back to defaults. `config/settings.example.json` documents all supported fields. Stop and close the app before editing advanced settings:

| Setting | Purpose |
| --- | --- |
| `confirmation`, `release`, `cooldown` | Gesture timing in seconds |
| `smoothing` | Exponential interpolation weight; lower is smoother but follows more slowly |
| `face_hold` | Hold last face pose briefly, then hide attached overlays (default 0.2 s) |
| `detection_width` | Inference input width (default 640); output retains camera resolution |

## Overlay library

### Tu primera reacción con tu propia imagen

1. Haz clic en **+ Subir mi imagen**, en la parte superior de la app. También puedes usar **+ Crear mi reacción** en **Mi estudio**.
2. En el editor, pulsa **1 · Subir mi imagen…** y elige un PNG, JPG o WebP de tu computadora. Un PNG transparente conserva el recorte; una foto JPG conserva su fondo.
3. Elige **Sobre mi rostro**, **Sobre mis ojos · gafas**, **Encima de mi cabeza** o **Fija en la pantalla**. Ajusta tamaño y posición viendo el resultado. Sin cámara aparece una vista de ejemplo claramente identificada; usa **Encender cámara para probar en mi rostro** para verte en vivo. Los cambios del editor aún no aparecen en OBS.
4. Pulsa **3 · Guardar y usar**. La reacción aparece en **Tu biblioteca** y se muestra si la cámara está encendida. Por defecto permanece hasta que vuelvas a hacer clic en su tarjeta o pulses **Quitar todas**; también puedes elegir una duración en el editor.
5. Usa **Editar / vincular** debajo de cualquier tarjeta para cambiar nombre, tamaño, posición o duración. Para activarla con una sonrisa u otra expresión, elige **Guardar y activar con una expresión →**: la imagen queda seleccionada en el asistente. Captura tu rostro relajado, captura la expresión y pulsa **4 · Guardar reacción automática**. Cierra ese asistente para reanudar la activación automática.

No necesitas configurar expresiones para usar tu imagen con un clic. Cancelar el editor no importa la imagen ni cambia la biblioteca. Los ajustes se guardan localmente; editar una reacción existente conserva sus vínculos a gestos.

Four original transparent placeholder PNGs are included in `assets/overlays/`. The asset generator only creates missing built-ins, so it never replaces your edits.

Use **+ Subir mi imagen** to open the visual editor. New imports default to face tracking and remain visible until toggled off (zero duration). The file is converted to an RGBA PNG in the library with a unique ID, shown with a thumbnail, and retained across launches. Existing transparency is preserved; opaque images remain opaque. Click its library tile to trigger or toggle it independently of gesture recognition; **Quitar todas** removes all active overlays. Very large images should be resized before import (8192-pixel maximum per dimension).

Metadata is in `config/overlays.json`. Supported properties are `id`, `name`, `file`, `type`, `anchor`, `duration`, `scale`, `offset_x`, `offset_y`, `rotation_mode`, and `tracking_mode`. Anchors are `top`, `center`, `bottom` for screen effects. Screen scale is a fraction of frame width; eyes scale multiplies eye distance; face scale multiplies face width. Offsets are fractions of frame width/height. `rotation_mode: face` follows head tilt; `none` stays upright. Tracking centers take precedence over screen anchors for attached effects. PNG is the only current renderer; the metadata type and compositor boundary allow future animation decoders.

Hand gesture behavior lives in `config/gestures.json`; replace an overlay ID there to assign your PNG to a hand gesture, then restart. Allowed actions: `toggle_overlay`, `show_overlay`, `clear_overlays`. Unknown hand gestures, actions, IDs, duplicate overlay IDs, unsafe paths, and invalid metadata fail startup with a clear error. Fix that file and relaunch. A hand mapping editor and GIF/video/audio effects are future work.

## Facial expression setup

Start the camera with **Encender cámara**, enable **Face tracking** under **Ajustes**, and click **Activar con mi expresión →** below the right panel, or use the expression action in the image editor. The separate, resizable window shares the running camera; it does not open another capture device. The **Tu rostro** tab shows a live face mesh even when preview debug is off. **Probar reacción** shows your composited output. Setup lines never enter the OBS output. Tracking parameters are hidden under **Mostrar datos de seguimiento**, and placement controls under **Ajustes de posición (opcional)**.

1. Import your image using **+ Subir mi imagen** in the main window or **+ Subir mi propia imagen…** in the expression assistant. Main-window controls and library tiles remain available while setup is open.
2. Choose **+ Nuevo gesto** and enter a name, such as smile, wink, raised eyebrows, or open mouth.
3. Relax your face and click **2 · Capturar rostro relajado (1 s)**; hold still for one second. Make your expression, click **3 · Capturar mi expresión (1 s)**, and hold it for one second. Each capture uses the median of at least five live samples. Face loss cancels a capture.
4. Watch the match meter as you repeat the expression. Lower **Sensibilidad del gesto** for greater sensitivity; raise it to require a stronger expression. The meter previews the selected unsaved template; automatic recognition uses saved values.
5. Choose **1 · Tu imagen**. Optional placement controls allow face/eye/screen tracking, size, X/Y position, duration, and head rotation. **Probar mi reacción** saves that image's placement and triggers it manually; view it under **Probar reacción**. Placement changes apply everywhere that image is used.
6. Click **4 · Guardar reacción automática**, then close setup to resume automatic triggers. Both hand and facial automatic effects are paused while setup is open; manual clicks remain enabled. Expressions use the same hold, release and cooldown settings as hand gestures, with independent timing. A held expression fires once; temporary effects expire and persistent effects remain until cleared or toggled manually.

Saved expressions can be selected, renamed, disabled, remapped, recalibrated or deleted in this window without restarting. Rules live in `config/facial_gestures.json`, created on the first save. Invalid rules produce a startup warning and disable facial rules until repaired or replaced through setup. Rules contain numeric blendshape samples and image IDs; no photos or video are stored. This feature tracks facial movement for effects rather than identifying people.

Expression matching uses up to six of the strongest changes from neutral among MediaPipe's [facial blendshape scores](https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker/python). All selected features must reach the configured proportion of the captured expression. Expressions too similar to neutral are rejected. Use distinct expressions, recalibrate for your camera and lighting, and test recognition in person; automated fixtures do not establish human recognition accuracy. Manual face-attached images still require a visible tracked face to position them, although they do not require any expression to be detected.

## OBS → Virtual Camera → Teams

1. Launch MemeCam.
2. Select your physical webcam.
3. Start camera.
4. Open **Output Window**. Its stable window title is **MemeCam Output**.
5. Open OBS Studio.
6. Add a **Window Capture** source to a scene.
7. Select **MemeCam Output**, use the Windows capture method available for that window, and disable **Capture Cursor**. Enable **Client Area** if offered so the OS title bar is excluded. Do not select the control window.
8. Fit the source to your canvas. A 1280×720 canvas at 30 FPS is a useful starting point. Click **Start Virtual Camera** in OBS.
9. Open Teams.
10. Select **OBS Virtual Camera** in Teams device/video settings. Discord, Zoom, and Google Meet can select the same camera.

The output surface contains only video and black letterboxing, preserves the source aspect ratio at any window size, and has no controls or status text in its pixels. **Borderless** removes OS window decorations; **Fullscreen** fills the screen. Escape exits fullscreen/borderless. The main controls stay available separately. Leave the output open and avoid minimizing it while OBS captures it. Default output is clean even when preview debug is enabled; **Include debug in output** is a separate explicit opt-in and starts off on each launch. Stop/failed camera clears both surfaces to prevent frozen private frames being left on screen.

If OBS is black, first make the output window visible, try the alternate Window Capture method, confirm the correct window, and match OBS/MemeCam privilege levels. Restart the conferencing app after starting OBS Virtual Camera if the device is missing. Camera selection and virtual-camera menus vary with application versions.

## Architecture

```text
Capture thread                Processing QThread                  Qt GUI thread
OpenCV device ──latest slot──→ MediaPipe hand + face ──latest slot─→ 16 ms poll
  drops old frames               ↓                                  ├─ Preview + debug
                              classifier                            └─ Clean Output
                                 ↓
                         confirmation / debounce
                                 ↓
                        configured gesture action
                                 ↓
                         overlay engine / RGBA
```

Camera discovery also runs off the GUI thread. Neither captured frames nor rendered frames build an unbounded event queue. UI commands are delivered to the processing worker, which alone owns its detectors and overlay state. Eye position, scale, center, and wrapped head angle are smoothed; short face loss holds the last pose, then attached effects hide until reacquisition. Model initialization and camera failures are shown in the control window. Stop/exit requests cooperative cleanup; camera and native model resources close in their owning threads. A driver that hangs beyond shutdown timeout blocks reopening until restart instead of racing a second device handle.

Modules: `camera/` capture/pipeline, `vision/` landmarks/classification/smoothing, `gestures/` temporal state and dispatch, `overlays/` models/assets/compositing, `config/` validation/persistence, `ui/` controls/output/video painting. There are no animation or sound implementations yet.

## Development and verification

```powershell
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.tmp\pytest
.\.venv\Scripts\python.exe -m ruff check memecam scripts tests
.\.venv\Scripts\python.exe -m compileall -q memecam scripts
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe scripts\verify_vision.py
.\.venv\Scripts\python.exe -m memecam --demo --smoke-test
.\.venv\Scripts\python.exe -m memecam --smoke-test
# Physical camera attempt; auto-exits for diagnostics:
.\.venv\Scripts\python.exe -m memecam --start-camera --quit-after 20
# Interactive synthetic preview without camera:
.\.venv\Scripts\python.exe -m memecam --demo
```

Tests cover timing, hold/release, cooldown, synthetic joint fixtures, smoothing and angle wrapping, lifetime/toggle/clear, RGBA clipping, hidden lost-face effects, configuration validation and roundtrips, custom PNG imports, threaded processing with a fake camera, shutdown/error recovery, single-slot delivery, and clean output ownership. Real model loading/inference is a separate explicit check so unit tests need no model downloads. See `docs/MANUAL_TESTS.md` for physical/OBS acceptance checks and `docs/VALIDATION.md` for results on this machine.

## Troubleshooting

- **Camera cannot open:** close apps using the physical webcam, verify Windows Settings → Privacy & security → Camera → access for desktop apps, reconnect the device, refresh, and retry. OBS should capture MemeCam's window, rather than opening that same webcam again.
- **Camera disconnects:** the app shows an error and clears video. Reconnect, refresh, select, and start again. If the driver itself stops responding, restart MemeCam.
- **Missing models:** run `scripts/setup_models.py` once online. Model files are not committed. Keep the manifest so subsequent downloads can verify exact hashes.
- **Import/DLL errors:** use `.venv\Scripts\python.exe`, Python 3.11/3.12 x64, and a fresh environment. Install the Microsoft Visual C++ x64 runtime if Windows reports missing runtime DLLs. Do not install another OpenCV distribution alongside `opencv-contrib-python`; they share the `cv2` namespace.
- **Slow video:** choose 640×480, disable one detector, reduce inference width, and use a well-lit view. Measured FPS includes inference and composition; processing milliseconds exclude USB sensor and OBS/conferencing buffering. No 30 FPS claim is made without physical measurement.
- **Gesture missed:** inspect debug landmarks, keep all fingers visible, hold longer than the configured confirmation period, and release between actions. Face glasses need face tracking enabled and visible eyes.
- **Unexpected errors:** check rotating `logs/memecam.log`. It records transitions rather than every frame. MediaPipe can print native informational/warning messages on stderr. Logs and settings are local and video is not recorded.
