import sqlite3
import os
import glob
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

def find_sqlite_files(directory="."):
    """Finds all SQLite files in the specified directory"""
    # Search for files with .sqlite or .db extensions
    sqlite_files = glob.glob(os.path.join(directory, "*.sqlite"))
    sqlite_files += glob.glob(os.path.join(directory, "*.db"))
    
    # Check files without extensions to see if they are SQLite databases
    for file in glob.glob(os.path.join(directory, "*")):
        if os.path.isfile(file) and not os.path.splitext(file)[1]:
            try:
                # Try to open the file as an SQLite database
                conn = sqlite3.connect(file)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                conn.close()
                # If the query succeeds, add the file to the list
                sqlite_files.append(file)
            except sqlite3.Error:
                # If an error occurs, the file is not an SQLite database
                pass
    
    return sqlite_files

def check_file_table(db_path):
    """Checks if the database contains a 'file' table"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='file'")
        result = cursor.fetchone() is not None
        conn.close()
        return result
    except sqlite3.Error:
        return False

class SQLiteMetaMaskViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("SQLite MetaMask ID Viewer v1.1")
        self.root.geometry("435x495")  
        self.root.resizable(True, True)
        
        # Configure colors
        self.root.configure(bg='#f0f0f0')
        
        # Configure grid for root
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        self.db_path = None
        self.conn = None
        
        self.setup_ui()
        
        # Automatically scan directory on startup
        self.scan_directory()
    
    def setup_ui(self):
        """Sets up the user interface"""
        # Main frame - using grid instead of pack
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.grid(row=0, column=0, sticky="nsew")
        main_frame.grid_rowconfigure(2, weight=1)  # Data frame will expand
        main_frame.grid_columnconfigure(0, weight=1)
        
        # Database selection section
        db_frame = ttk.LabelFrame(main_frame, text="Database", padding="10")
        db_frame.grid(row=0, column=0, sticky="ew", pady=5)
        
        # Database path label and entry
        ttk.Label(db_frame, text="Database path:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        # Entry and browse button
        entry_frame = ttk.Frame(db_frame)
        entry_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        entry_frame.grid_columnconfigure(0, weight=1)
        
        self.db_path_var = tk.StringVar()
        ttk.Entry(entry_frame, textvariable=self.db_path_var).grid(row=0, column=0, sticky="ew", padx=(0, 5))
        ttk.Button(entry_frame, text="Browse", command=self.browse_db, style="Browse.TButton").grid(row=0, column=1)
        
        # Buttons for database operations
        button_frame = ttk.Frame(db_frame)
        button_frame.grid(row=2, column=0, pady=5)
        
        ttk.Button(button_frame, text="Load Database", command=self.load_database, style="Load.TButton").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Scan Directory", command=self.scan_directory, style="Scan.TButton").pack(side=tk.LEFT)
        
        # Configure grid weights
        db_frame.grid_columnconfigure(0, weight=1)
        
        # Section for displaying found databases
        self.db_list_frame = ttk.LabelFrame(main_frame, text="Found databases with 'file' table", padding="10")
        self.db_list_frame.grid(row=1, column=0, sticky="ew", pady=5)
        
        # Frame for listbox and scrollbar
        listbox_frame = ttk.Frame(self.db_list_frame)
        listbox_frame.pack(fill=tk.X, expand=True)
        
        # Listbox for found databases
        self.db_listbox = tk.Listbox(listbox_frame, height=4, font=("Consolas", 9))
        self.db_listbox.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbar for databases, shown only if needed
        self.db_scrollbar = ttk.Scrollbar(listbox_frame, orient=tk.VERTICAL, command=self.db_listbox.yview)
        self.db_listbox.configure(yscrollcommand=self.db_scrollbar.set)
        
        self.db_listbox.bind("<Double-1>", self.on_db_select)
        
        # Data display section
        data_frame = ttk.LabelFrame(main_frame, text="ID values from 'file' table", padding="10")
        data_frame.grid(row=2, column=0, sticky="nsew", pady=5)
        data_frame.grid_rowconfigure(0, weight=1)
        data_frame.grid_columnconfigure(0, weight=1)
        
        # Frame for data with copy functionality
        self.data_container = ttk.Frame(data_frame)
        self.data_container.grid(row=0, column=0, sticky="nsew")
        self.data_container.grid_rowconfigure(0, weight=1)
        self.data_container.grid_columnconfigure(0, weight=1)
        
        # Scrollable frame for ID values - scrollbar always visible
        self.canvas = tk.Canvas(self.data_container, bg='white', height=150, highlightthickness=0, bd=0, relief='flat')
        self.data_scrollbar = ttk.Scrollbar(self.data_container, orient=tk.VERTICAL, command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.update_scroll_region()
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.data_scrollbar.set)
        
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.data_scrollbar.grid(row=0, column=1, sticky="ns")  # Scrollbar always visible
        
        # Status bar
        status_frame = tk.Frame(self.root, bg='#e0e0e0', relief=tk.SUNKEN, bd=1)
        status_frame.grid(row=1, column=0, sticky="ew")
        status_frame.grid_columnconfigure(0, weight=1)
        
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        
        # Status label with padding
        self.status_label = tk.Label(status_frame, textvariable=self.status_var, 
                                   bg='#e0e0e0', fg='#333333', font=("Arial", 9),
                                   anchor=tk.W, padx=10, pady=3)
        self.status_label.grid(row=0, column=0, sticky="ew")
    
    def update_scroll_region(self):
        """Updates the scroll region and always shows the scrollbar"""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def update_db_scrollbar(self):
        """Updates the scrollbar for databases as needed"""
        total_items = self.db_listbox.size()
        visible_items = int(self.db_listbox.cget('height'))
        
        if total_items > visible_items:
            self.db_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        else:
            self.db_scrollbar.pack_forget()
    
    def copy_to_clipboard(self, text, button):
        """Copies text to clipboard and changes button color"""
        self.root.clipboard_clear()
        self.root.clipboard_append(str(text))
        self.root.update()
        self.status_var.set(f"ID {text} copied to clipboard")
        
        # Change button color on click
        button.configure(bg="#3e8e41")
        
        # Show temporary confirmation
        self.root.after(2000, lambda: self.status_var.set("Ready"))
        # Revert button color
        self.root.after(2000, lambda: button.configure(bg="#4CAF50"))
    
    def scan_directory(self):
        """Scans the current directory for SQLite databases with 'file' table"""
        self.status_var.set("Scanning directory...")
        self.root.update()
        
        # Clear the listbox
        self.db_listbox.delete(0, tk.END)
        
        # Get current directory
        current_dir = os.getcwd()
        
        # Find all SQLite files
        sqlite_files = find_sqlite_files(current_dir)
        
        # Check which databases contain the 'file' table
        valid_dbs = []
        for db_file in sqlite_files:
            if check_file_table(db_file):
                valid_dbs.append(db_file)
                # Display only the file name (without path)
                display_name = os.path.basename(db_file)
                self.db_listbox.insert(tk.END, display_name)
        
        if not valid_dbs:
            self.status_var.set("No SQLite databases with 'file' table found")
            # Clear data display
            for widget in self.scrollable_frame.winfo_children():
                widget.destroy()
        else:
            self.status_var.set(f"Found {len(valid_dbs)} databases with 'file' table")
            # Automatically load the first found database
            if valid_dbs:
                first_db = valid_dbs[0]
                self.db_path_var.set(first_db)
                self.load_database()
                # Select the first item in the listbox
                self.db_listbox.selection_set(0)
        
        # Update scrollbar for databases
        self.update_db_scrollbar()
    
    def on_db_select(self, event):
        """Handles database selection from the listbox"""
        selection = self.db_listbox.curselection()
        if selection:
            index = selection[0]
            db_name = self.db_listbox.get(index)
            
            # Find the database by name in the current directory
            current_dir = os.getcwd()
            sqlite_files = find_sqlite_files(current_dir)
            
            for db_file in sqlite_files:
                if os.path.basename(db_file) == db_name and check_file_table(db_file):
                    self.db_path_var.set(db_file)
                    self.load_database()
                    break
    
    def browse_db(self):
        """Opens a dialog to select a database file"""
        file_path = filedialog.askopenfilename(
            title="Select SQLite Database",
            filetypes=[("SQLite Databases", "*.sqlite"), ("All Files", "*.*")]
        )
        if file_path:
            self.db_path_var.set(file_path)
    
    def load_database(self):
        """Loads the database and displays data from the 'file' table"""
        db_path = self.db_path_var.get()
        if not db_path:
            messagebox.showerror("Error", "No database path specified!")
            return
        
        if not os.path.exists(db_path):
            messagebox.showerror("Error", f"File '{db_path}' does not exist!")
            return
        
        try:
            # Close previous connection if it exists
            if self.conn:
                self.conn.close()
            
            # Connect to the database
            self.conn = sqlite3.connect(db_path)
            self.db_path = db_path
            
            # Check if 'file' table exists
            cursor = self.conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='file';")
            if not cursor.fetchone():
                messagebox.showerror("Error", "'file' table not found in the database!")
                self.conn.close()
                self.conn = None
                return
            
            # Load data from 'file' table
            self.refresh_data()
            
            self.status_var.set(f"Database loaded: {os.path.basename(db_path)}")
        
        except sqlite3.Error as e:
            messagebox.showerror("Error", f"Database error: {e}")
            if self.conn:
                self.conn.close()
                self.conn = None
    
    def refresh_data(self):
        """Refreshes the display of data from the 'file' table"""
        if not self.conn:
            return
        
        # Clear previous data
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        try:
            # Load data from 'file' table
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM file ORDER BY id")
            rows = cursor.fetchall()
            
            if not rows:
                no_data_label = ttk.Label(self.scrollable_frame, text="No data in 'file' table", 
                                        font=("Arial", 12), foreground="gray")
                no_data_label.pack(pady=20)
                self.status_var.set("Database loaded - no data")
                return
            
            # Create header with improved style
            header_frame = tk.Frame(self.scrollable_frame, bg="#2c3e50", relief=tk.FLAT)
            header_frame.pack(fill=tk.X, pady=(0, 0))
            
            # Configure grid weights for header
            header_frame.grid_columnconfigure(0, weight=4, minsize=200)  # ID column wider
            header_frame.grid_columnconfigure(1, weight=2, minsize=80)   # RefCount column
            header_frame.grid_columnconfigure(2, weight=1, minsize=70)   # Action column narrower
            
            # Column headers
            id_header = tk.Label(header_frame, text="ID", 
                               font=("Arial", 12, "bold"), 
                               foreground="white", bg="#2c3e50",
                               anchor="w", padx=10, pady=8)
            id_header.grid(row=0, column=0, sticky="ew")
            
            refcount_header = tk.Label(header_frame, text="RefCount", 
                                     font=("Arial", 12, "bold"), 
                                     foreground="white", bg="#2c3e50",
                                     anchor="w", padx=10, pady=8)
            refcount_header.grid(row=0, column=1, sticky="ew")
            
            action_header = tk.Label(header_frame, text="Action", 
                                   font=("Arial", 12, "bold"), 
                                   foreground="white", bg="#2c3e50",
                                   anchor="center", padx=10, pady=8)
            action_header.grid(row=0, column=2, sticky="ew")
            
            # Separator line under header
            separator = tk.Frame(self.scrollable_frame, height=2, bg="#34495e")
            separator.pack(fill=tk.X)
            
            # Display data with COPY buttons
            for i, row in enumerate(rows):
                id_value, refcount = row
                
                # Frame for one row with alternating background
                row_frame = tk.Frame(self.scrollable_frame, 
                                   bg="#f8f9fa" if i % 2 == 0 else "#ffffff",
                                   relief=tk.FLAT, bd=0)
                row_frame.pack(fill=tk.X, pady=1)
                
                # Configure grid weights for consistent layout
                row_frame.grid_columnconfigure(0, weight=4, minsize=200)  # ID column
                row_frame.grid_columnconfigure(1, weight=2, minsize=80)   # RefCount column
                row_frame.grid_columnconfigure(2, weight=1, minsize=70)   # Button column
                
                # ID value with background
                id_frame = tk.Frame(row_frame, bg=row_frame["bg"])
                id_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
                
                id_label = tk.Label(id_frame, text=str(id_value), 
                                  font=("Consolas", 11, "bold"), 
                                  foreground="#1976d2", bg=row_frame["bg"],
                                  anchor="w")
                id_label.pack(fill=tk.X)
                
                # RefCount value with background
                refcount_frame = tk.Frame(row_frame, bg=row_frame["bg"])
                refcount_frame.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
                
                refcount_label = tk.Label(refcount_frame, text=str(refcount), 
                                        font=("Consolas", 11), 
                                        foreground="#424242", bg=row_frame["bg"],
                                        anchor="w")
                refcount_label.pack(fill=tk.X)
                
                # Improved COPY button - stretched and centered
                copy_button = tk.Button(row_frame, text="COPY", 
                                      bg="#4CAF50", fg="white", 
                                      font=("Arial", 9, "bold"),
                                      relief=tk.FLAT, bd=0, 
                                      highlightthickness=0,
                                      padx=6, pady=4,
                                      width=8,  # Fixed width for uniformity
                                      cursor="hand2",
                                      activebackground="#45a049",
                                      activeforeground="white")
                copy_button.grid(row=0, column=2, sticky="ew", padx=5, pady=3)  # Stretched within column
                
                # Assign command function
                copy_button.configure(command=lambda val=id_value, btn=copy_button: self.copy_to_clipboard(val, btn))
                
                # Hover effect for button
                def on_enter(e, btn=copy_button):
                    btn.configure(bg="#45a049")
                
                def on_leave(e, btn=copy_button):
                    btn.configure(bg="#4CAF50")
                
                copy_button.bind("<Enter>", on_enter)
                copy_button.bind("<Leave>", on_leave)
                
                # Thin separator line between rows
                if i < len(rows) - 1:  # Not on the last row
                    separator_line = tk.Frame(self.scrollable_frame, height=1, bg="#e0e0e0")
                    separator_line.pack(fill=tk.X)
            
            self.status_var.set(f"Displayed {len(rows)} ID values from database {os.path.basename(self.db_path)}")
            
            # Update scroll region
            self.update_scroll_region()
        
        except sqlite3.Error as e:
            messagebox.showerror("Error", f"Error loading data: {e}")
            self.status_var.set("Error loading data")

def main():
    root = tk.Tk()
    
    # Configure styles
    style = ttk.Style()
    style.theme_use('clam')
    
    # Button colors - no relief for smooth look
    style.configure("Browse.TButton", background="#2196F3", foreground="white", relief="flat", borderwidth=0)
    style.map("Browse.TButton", background=[('active', '#0b7dda')])
    
    style.configure("Load.TButton", background="#FF9800", foreground="white", relief="flat", borderwidth=0)
    style.map("Load.TButton", background=[('active', '#e68a00')])
    
    style.configure("Scan.TButton", background="#9C27B0", foreground="white", relief="flat", borderwidth=0)
    style.map("Scan.TButton", background=[('active', '#89219b')])
    
    style.configure("Refresh.TButton", background="#009688", foreground="white", relief="flat", borderwidth=0)
    style.map("Refresh.TButton", background=[('active', '#00796b')])
    
    # Style for rows
    style.configure("Even.TFrame", background="#e0e0e0")
    
    app = SQLiteMetaMaskViewer(root)
    
    # Set window icon (if available)
    try:
        root.iconbitmap('images/icon.ico')
    except:
        pass
    
    root.mainloop()

if __name__ == "__main__":
    main()