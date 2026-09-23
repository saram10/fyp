"""
desktop_launcher.py
Entry point used to package ExpenseTracker as a standalone desktop app
(via PyInstaller). Double-clicking the resulting .exe runs this file, which
starts Streamlit's server in the same process and opens the app in the
user's default browser automatically — no terminal, no commands, no Python
installation required on the recipient's machine.

This is NOT needed for normal development use — for that, just run:
    streamlit run app.py
"""
import os
import sys


def resource_path(filename):
    """
    Resolves the path to a bundled file whether running from source or from
    inside a PyInstaller-built executable (which extracts bundled files to a
    temporary folder referenced by sys._MEIPASS at runtime).
    """
    base_dir = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, filename)


def main():
    from streamlit.web import cli as stcli

    app_path = resource_path("app.py")

    sys.argv = [
        "streamlit",
        "run",
        app_path,
        "--global.developmentMode=false",
        "--server.headless=false",
        "--server.port=8501",
        "--server.showEmailPrompt=false",
        "--browser.gatherUsageStats=false",
    ]
    sys.exit(stcli.main())


if __name__ == "__main__":
    main()
