"""
Role selector dialog for choosing Master or Worker mode.
Appears at startup to determine application behavior.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import sys


class RoleSelector(tk.Toplevel):
    """Dialog for selecting Master or Worker role."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.title("WiFi Distributed Computing - Role Selection")
        self.geometry("600x500")
        self.resizable(False, False)
        self.selected_role = None
        
        # Configure colors
        self.bg_color = "#f0f0f0"
        self.configure(bg=self.bg_color)
        
        self._create_widgets()
        self._center_window()
    
    def _center_window(self):
        """Center window on screen."""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
    
    def _create_widgets(self):
        """Create selector widgets."""
        # Header
        header_frame = tk.Frame(self, bg="#2c3e50", height=80)
        header_frame.pack(fill="x")
        
        tk.Label(header_frame, text="WiFi Distributed Computing System",
                font=("Arial", 16, "bold"), fg="white", bg="#2c3e50").pack(pady=20)
        
        tk.Label(header_frame, text="Select Your Role",
                font=("Arial", 12), fg="#ecf0f1", bg="#2c3e50").pack(pady=(0, 10))
        
        # Main container
        main_frame = tk.Frame(self, bg=self.bg_color)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Master option
        master_frame = self._create_role_card(main_frame, "Master", "#2196F3",
                                             "Distribute tasks across workers",
                                             ["• Task distribution", "• Result aggregation",
                                              "• Node discovery", "• Progress monitoring"])
        master_frame.pack(fill="both", expand=True, pady=10)
        master_frame.bind("<Button-1>", lambda e: self._select_role("master"))
        
        # Worker option
        worker_frame = self._create_role_card(main_frame, "Worker", "#4CAF50",
                                             "Execute distributed tasks",
                                             ["• Task execution", "• File attachment support",
                                              "• Auto-discovery", "• Real-time status"])
        worker_frame.pack(fill="both", expand=True, pady=10)
        worker_frame.bind("<Button-1>", lambda e: self._select_role("worker"))
        
        # Info text
        info_frame = tk.LabelFrame(main_frame, text="System Information", 
                                  font=("Arial", 10, "bold"), bg=self.bg_color)
        info_frame.pack(fill="x", pady=20)
        
        info_text = ("Master: Coordinates task distribution and result aggregation\n"
                    "Worker: Executes tasks assigned by Master nodes\n\n"
                    "Both can auto-discover each other on the same WiFi network")
        
        tk.Label(info_frame, text=info_text, font=("Arial", 9),
                bg=self.bg_color, justify="left", wraplength=550).pack(padx=10, pady=10)
        
        # Buttons
        button_frame = tk.Frame(self, bg=self.bg_color)
        button_frame.pack(fill="x", padx=20, pady=20)
        
        tk.Button(button_frame, text="Exit", command=self._exit_app,
                 bg="#757575", fg="white", width=15).pack(side="right", padx=5)
    
    def _create_role_card(self, parent, role_name: str, color: str, 
                         description: str, features: list):
        """Create a role selection card."""
        card = tk.Frame(parent, bg="white", relief="raised", borderwidth=2)
        card.config(cursor="hand2")
        
        # Bind hover effects
        def on_enter(e):
            card.config(bg="#e8f5e9" if role_name == "Worker" else "#e3f2fd")
        
        def on_leave(e):
            card.config(bg="white")
        
        card.bind("<Enter>", on_enter)
        card.bind("<Leave>", on_leave)
        
        # Header with color
        header = tk.Frame(card, bg=color, height=40)
        header.pack(fill="x")
        header.bind("<Button-1>", lambda e: self._select_role(role_name.lower()))
        
        tk.Label(header, text=role_name, font=("Arial", 14, "bold"),
                fg="white", bg=color).pack(pady=10)
        
        # Content
        content = tk.Frame(card, bg="white")
        content.pack(fill="both", expand=True, padx=15, pady=15)
        content.bind("<Button-1>", lambda e: self._select_role(role_name.lower()))
        
        tk.Label(content, text=description, font=("Arial", 10),
                bg="white", fg="#333").pack(anchor="w", pady=(0, 10))
        
        # Features list
        for feature in features:
            tk.Label(content, text=feature, font=("Arial", 9),
                    bg="white", fg="#666").pack(anchor="w", padx=10)
        
        # Select button
        tk.Button(content, text=f"Select {role_name}", command=lambda: self._select_role(role_name.lower()),
                 bg=color, fg="white", font=("Arial", 10, "bold"),
                 width=20).pack(pady=10)
        
        return card
    
    def _select_role(self, role: str):
        """Select a role and close dialog."""
        self.selected_role = role.lower()
        self.destroy()
    
    def _exit_app(self):
        """Exit application."""
        if messagebox.askokcancel("Exit", "Are you sure you want to exit?"):
            sys.exit(0)


def show_role_selector(parent=None):
    """Show role selector and return selected role."""
    dialog = RoleSelector(parent)
    dialog.wait_window()
    return dialog.selected_role
