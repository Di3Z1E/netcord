import sys
import os

# Add src to sys.path to allow importing the netcord package directly
# This is still needed for development but PyInstaller will use 'pathex'
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "src"))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from netcord.app import NetCordApp

def main():
    if sys.platform != "win32":
        print("NetCord is designed for Windows only.")
        sys.exit(1)

    app = NetCordApp()
    app.mainloop()

if __name__ == "__main__":
    main()
