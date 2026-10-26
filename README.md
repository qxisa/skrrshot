# Shotool

A smart screenshot tool for Ubuntu. Press the shortcut, pick a mode or just drag a region, and the capture lands on your clipboard.

Version 0.2 covers capture, the preview card, batches, saving, and convert or compress, on X11.

## Install

    git clone https://github.com/qxisa/skrrshot.git
    cd skrrshot
    ./install.sh

The installer adds the dependencies (python3-gi, python3-gi-cairo, gir1.2-gtk-3.0), registers the shortcut, and sets Shotool to start on login.

The default shortcut is Super+Shift+S. The background process listens for the shortcut itself, so it does not depend on GNOME settings. The installer checks the existing GNOME and custom shortcuts and falls back to Ctrl+Super+S, then Ctrl+Alt+Shift+S, if one is taken. To choose your own, pass it as the first argument, for example `./install.sh '<Primary><Alt>p'`, or run `shotool hotkey '<Primary><Alt>p'` later.

## Use

- The shortcut opens the mode menu at the cursor. Arrow keys move, Enter picks, 1 to 4 pick directly, Esc or right click cancels.
- Dragging anywhere skips the menu and selects a region.
- Every capture is copied to the clipboard and a card shows a preview with options: Save, Add to batch, Convert or compress.
- The card fades after a few seconds. Click an option, or move the mouse onto the card and use arrows, Enter and the letter keys.
- Batch: add several captures, then open the menu again and pick Batch. Choose a format and save everything to a folder, or as one multi-page PDF.
- Convert or compress: PNG, JPEG, PDF, plus WebP and AVIF when the system has the image loaders for them. JPEG and WebP have a quality setting with a size estimate.
- Saving opens at the last folder you used. Format and quality are remembered.

## Update

    shotool update

## Remove

    ./uninstall.sh

## Roadmap

1. Capture core
2. Preview card, batch, save with remembered folder, convert and compress (this release)
3. Upload with consent, AI handoff, annotation and redaction
4. OCR, history, settings, .deb packaging, Wayland support

## Known limits

- X11 only. On Wayland the command exits with a message.
- The launcher always uses /usr/bin/python3, so conda and virtualenv do not affect it.
- Window capture uses the window frame reported by the window manager, so shadows on some apps may be included.
- HiDPI scaling has not been tested yet.
