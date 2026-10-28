# Physical acceptance checklist

Use normal lighting, a single person and one visible hand. Record device, resolution, CPU, measured FPS, and observations. Automated fixtures do not establish recognition accuracy or meeting latency.

1. Start normally, discover/select the webcam, use 720p/30, and start. Verify dimensions, a moving preview, measured FPS, and responsive window dragging/controls.
2. Enable preview debug. Verify 21 hand landmarks and face landmarks align when mirrored and unmirrored. Disable either detector while live; verify the other and manual PNG triggers continue.
3. Briefly flash each gesture (<200 ms): no action. Hold peace for >350 ms: glasses appear once. Hold for 4 seconds: no toggle-off. Release >250 ms and repeat: glasses toggle off. Repeat for both hands.
4. Hold thumbs up for 4 seconds: Approved appears once and disappears after 2 seconds. Release, repeat, and verify it reappears. Check thumbs down and open palm. Show ambiguous/partial fingers: prefer no trigger. Check rapid changes against the cooldown.
5. With glasses active, move laterally, change distance, and tilt head. Verify centering, scale, rotation, and smooth movement. Leave frame briefly, then for >200 ms: pose holds briefly, then attached glasses hide. Reenter without a wild jump. Fist clears persistent and temporary effects.
6. Open Output Window while preview debug is on: clean output contains no landmarks/text. Resize to several aspect ratios, toggle borderless/fullscreen, exit with Escape. Explicit output debug should show debug only when selected.
7. In OBS add Window Capture → MemeCam Output, cursor off, client area selected. Verify no control UI/title bar in capture, stable framing, and continuous motion while interacting with main controls. Start OBS Virtual Camera and verify in Teams, Discord, Zoom or Meet. Leave audio unchanged.
8. Add an RGBA PNG through the dialog; test screen and eyes/face modes, lifetime zero, tile activation, and clear. Restart; imported PNGs and settings should remain. Set a custom gesture ID in the mappings and confirm after restart.
9. Stop/start camera at least five times. Unplug while live, reconnect and restart. Try a camera held by another app. UI must stay usable, show actionable errors, and clear old frames. Exit while initializing and while live. Verify camera LED turns off after cleanup.
10. Run for 10 minutes; record processed FPS and OBS latency observations. Minimize the controls while leaving output visible. Verify no growing delay, repeated held-gesture effects, or unexpected log errors. Test disconnected from the internet after setup.

OBS/conferencing integration, human landmark accuracy and real sensor latency require this hands-on pass; synthetic tests alone cannot sign them off.

## Facial expressions and manual placement

1. Import an opaque JPG and a transparent PNG. Select face tracking, trigger each tile without making an expression, and check that the images follow head position/scale/tilt. Verify transparency, duration, click-to-remove, and Clear.
2. Open **Configurar gestos faciales**. With preview debug disabled, verify the live mesh follows eyes, eyebrows and mouth. Confirm neither the mesh nor the setup UI enters the clean Output Window or OBS capture.
3. Capture one second of neutral, then a distinct smile or open mouth. Watch the learned parameter values and match meter. Capture a weak expression to check rejection; move out of frame during capture to check cancellation. With face tracking disabled or camera stopped, capture must be unavailable and no stale video should remain after stop.
4. Link your imported image, adjust its size/position/rotation/duration, and click **Aplicar posición y probar imagen**. Check the Result tab and manual library controls. Save the expression and close setup; repeat it and verify the configured hold, single activation while held, release/rearm and cooldown.
5. Save a second distinct expression. Switch between expressions; disable, remap, rename and delete saved rules. Restart and verify remaining rules and placement persist. Repeat with mirroring on/off, head movement, normal blinking and different lighting; note false activations and adjust sensitivity or recapture.
6. While setup is open, make saved hand and facial gestures; neither should automatically fire an effect. Manual triggers must still work. Stop/start while setup remains open; setup should resume its live feed, keep auto effects paused, and resume recognition on close.
