# Desktop resources

The native client also uses `background.jpg` as its Qt-painted background image.

Place the custom application icons here before building:

- `app.ico` for Windows
- `app.icns` for macOS

The PyInstaller spec treats both files as optional. Without them, the platform default icon is used.
