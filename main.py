import sys
from src.netcord.app import NetCordApp

if __name__ == "__main__":
    if sys.platform != "win32":
        print("NetCord is designed for Windows only.")
        sys.exit(1)

    app = NetCordApp()
    app.mainloop()
