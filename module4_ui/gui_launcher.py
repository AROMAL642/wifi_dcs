"""
Launcher script for the WiFi Distributed Computing GUI.
Handles checks and initialization before starting the GUI.
"""

import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

def check_requirements():
    """Check if required modules are available."""
    required_modules = ["tkinter"]
    missing = []
    
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing.append(module)
    
    if missing:
        messagebox.showerror(
            "Missing Dependencies",
            f"Missing required modules: {', '.join(missing)}\n\n"
            "Please install them using:\npip install -r requirements.txt"
        )
        return False
    
    return True

def main():
    """Start the GUI."""
    if not check_requirements():
        sys.exit(1)
    
    try:
        from gui import main as gui_main
        gui_main()
    except Exception as e:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Error", f"Failed to start GUI:\n{str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
