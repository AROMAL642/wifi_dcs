"""
Main entry point for the WiFi Distributed Computing GUI.
Allows user to select Master or Worker role.
"""

import tkinter as tk
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from role_selector import show_role_selector
from master_gui import MasterGUI
from worker_gui import WorkerGUI


def main():
    """Main application entry point."""
    # Create hidden root for role selection
    root = tk.Tk()
    root.withdraw()
    
    # Show role selector
    selected_role = show_role_selector(root)
    
    if not selected_role:
        sys.exit(0)
    
    root.destroy()
    
    # Create main window
    root = tk.Tk()
    
    if selected_role == "master":
        gui = MasterGUI(root)
        def on_closing():
            gui.cleanup()
            root.destroy()
    else:
        gui = WorkerGUI(root)
        def on_closing():
            gui.cleanup()
            root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
