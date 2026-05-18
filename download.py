import sys

try:
    from tubeswift.app import main
    FALLBACK_CLI = False
except ModuleNotFoundError as exc:
    if exc.name in {"_tkinter", "tkinter"}:
        from tubeswift.cli import main
        FALLBACK_CLI = True

        print("Tkinter is missing. Falling back to CLI mode.")
        print("For GUI mode install Tkinter support for your Python build.")
    else:
        raise


if __name__ == "__main__":
    if FALLBACK_CLI and len(sys.argv) == 1:
        print("")
        print("No URL provided. CLI mode needs a URL argument.")
        print('Example: python download.py "https://www.youtube.com/watch?v=VIDEO_ID"')
        print("To restore GUI mode, install Tkinter for this Python build:")
        print("  macOS (Homebrew Python 3.11): brew install python-tk@3.11")
        print("  Ubuntu/Debian: sudo apt install python3-tk")
        sys.exit(1)

    result = main()
    if isinstance(result, int):
        sys.exit(result)
