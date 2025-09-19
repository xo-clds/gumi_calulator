import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from datetime import datetime
import re
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib

matplotlib.use("TkAgg")
DB_FILE = "bmi_records.db"

# ---------------- Database ----------------
class BMIDatabase:
    def __init__(self, db_file=DB_FILE):
        self.conn = sqlite3.connect(db_file)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                weight REAL,
                height_m REAL,
                bmi REAL,
                category TEXT,
                date TEXT
            )
        """)
        self.conn.commit()

    def add_record(self, name, weight, height_m, bmi, category, date):
        self.conn.execute(
            "INSERT INTO records (name, weight, height_m, bmi, category, date) VALUES (?, ?, ?, ?, ?, ?)",
            (name, weight, height_m, bmi, category, date)
        )
        self.conn.commit()

    def get_users(self):
        cur = self.conn.cursor()
        cur.execute("SELECT DISTINCT name FROM records")
        return [r[0] for r in cur.fetchall()]

    def get_records(self, name):
        cur = self.conn.cursor()
        cur.execute("SELECT weight, height_m, bmi, category, date FROM records WHERE name=? ORDER BY date", (name,))
        return cur.fetchall()

    def get_last_visit(self, name):
        cur = self.conn.cursor()
        cur.execute("SELECT date FROM records WHERE name=? ORDER BY date DESC LIMIT 1", (name,))
        result = cur.fetchone()
        return datetime.fromisoformat(result[0]) if result else None

    def close(self):
        self.conn.close()

# ---------------- BMI Functions ----------------
def calculate_bmi(weight, height_m):
    return weight / (height_m ** 2)

def classify_bmi(bmi):
    if bmi < 18.5: return "Underweight"
    elif bmi < 25: return "Normal"
    elif bmi < 30: return "Overweight"
    else: return "Obese"

def parse_height(height_str):
    """Parse height like 5'4 into meters"""
    nums = re.findall(r"\d+", height_str)
    if not nums: raise ValueError("Invalid height format. Use e.g. 5'4")
    feet = int(nums[0])
    inches = int(nums[1]) if len(nums) > 1 else 0
    total_inches = feet * 12 + inches
    return total_inches * 0.0254

# ---------------- GUI ----------------
class BMIGUI:
    def __init__(self, root):
        self.db = BMIDatabase()
        self.root = root
        root.title("BMI Calculator (Dark Theme)")

        # Colors
        self.bg_color = "#2e2e2e"
        self.fg_color = "#f0f0f0"
        self.btn_color = "#444444"

        root.configure(bg=self.bg_color)

        # Input
        tk.Label(root, text="Name:", bg=self.bg_color, fg=self.fg_color).grid(row=0, column=0, sticky='w', padx=5)
        self.name_var = tk.StringVar()
        name_entry = tk.Entry(root, textvariable=self.name_var, bg="#3c3c3c", fg=self.fg_color, insertbackground=self.fg_color)
        name_entry.grid(row=0, column=1, padx=5, pady=2)
        name_entry.bind("<FocusOut>", self.show_last_visit)

        tk.Label(root, text="Weight (kg):", bg=self.bg_color, fg=self.fg_color).grid(row=1, column=0, sticky='w', padx=5)
        self.weight_var = tk.StringVar()
        tk.Entry(root, textvariable=self.weight_var, bg="#3c3c3c", fg=self.fg_color, insertbackground=self.fg_color).grid(row=1, column=1, padx=5, pady=2)

        tk.Label(root, text="Height (e.g. 5'4):", bg=self.bg_color, fg=self.fg_color).grid(row=2, column=0, sticky='w', padx=5)
        self.height_var = tk.StringVar()
        tk.Entry(root, textvariable=self.height_var, bg="#3c3c3c", fg=self.fg_color, insertbackground=self.fg_color).grid(row=2, column=1, padx=5, pady=2)

        # Buttons
        tk.Button(root, text="Calculate BMI", bg=self.btn_color, fg=self.fg_color, command=self.calculate).grid(row=3, column=0, pady=5)
        tk.Button(root, text="Save Record", bg=self.btn_color, fg=self.fg_color, command=self.save_record).grid(row=3, column=1, pady=5)

        # Result (2 lines)
        self.result_label = tk.Label(root, text="", bg=self.bg_color, fg=self.fg_color, font=("Arial", 12, "bold"), justify='left')
        self.result_label.grid(row=4, column=0, columnspan=2, pady=5)

        # History
        tk.Label(root, text="Saved Users:", bg=self.bg_color, fg=self.fg_color).grid(row=5, column=0, sticky='w', padx=5)
        self.user_combo = ttk.Combobox(root, values=self.db.get_users(), state="readonly")
        self.user_combo.grid(row=5, column=1, padx=5, pady=2)
        tk.Button(root, text="Load History", bg=self.btn_color, fg=self.fg_color, command=self.load_history).grid(row=6, column=0, columnspan=2, pady=5)

        self.history_list = tk.Listbox(root, width=50, bg="#3c3c3c", fg=self.fg_color)
        self.history_list.grid(row=7, column=0, columnspan=2, pady=5)

        # Plot
        self.figure = Figure(figsize=(5,2.5), facecolor="#2e2e2e")
        self.ax = self.figure.add_subplot(111)
        self.ax.set_facecolor("#2e2e2e")
        self.canvas = FigureCanvasTkAgg(self.figure, master=root)
        self.canvas.get_tk_widget().grid(row=8, column=0, columnspan=2, pady=5)

    # Last Visit
    def show_last_visit(self, event=None):
        name = self.name_var.get().strip()
        if name:
            last_visit = self.db.get_last_visit(name)
            if last_visit:
                messagebox.showinfo("Welcome Back", f"Welcome back, {name}! Your last visit was on {last_visit.strftime('%Y-%m-%d %H:%M:%S')}")

    # Calculate BMI
    def calculate(self):
        try:
            weight = float(self.weight_var.get())
            height_m = parse_height(self.height_var.get())
            bmi = calculate_bmi(weight, height_m)
            category = classify_bmi(bmi)
            self.current_bmi = bmi
            self.current_category = category
            # 2-line result
            self.result_label.config(text=f"BMI: {bmi:.2f}\nCategory: {category}")
        except:
            self.result_label.config(text="Invalid input!")

    # Save Record
    def save_record(self):
        try:
            name = self.name_var.get().strip()
            if not name: raise ValueError("Enter a name")
            self.db.add_record(name, float(self.weight_var.get()), parse_height(self.height_var.get()), self.current_bmi, self.current_category, datetime.now().isoformat())
            messagebox.showinfo("Saved", f"Record saved for {name}")
            self.user_combo['values'] = self.db.get_users()
            self.update_bmi_plot(name)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # Load History
    def load_history(self):
        user = self.user_combo.get()
        if user:
            self.update_bmi_plot(user)

    # Update BMI Trend Plot
    def update_bmi_plot(self, user):
        records = self.db.get_records(user)
        self.history_list.delete(0, tk.END)
        self.ax.clear()
        self.ax.set_facecolor("#2e2e2e")
        dates = []
        bmis = []

        for r in records:
            weight, height, bmi, category, date = r
            self.history_list.insert(tk.END, f"{date} - BMI:{bmi:.2f} ({category})")
            dates.append(datetime.fromisoformat(date))
            bmis.append(bmi)

        if dates:
            self.ax.plot(dates, bmis, marker='o', linestyle='-', color='cyan')
            self.ax.set_title(f"{user}'s BMI Trend", color="white")
            self.ax.set_xlabel("Date", color="white")
            self.ax.set_ylabel("BMI", color="white")
            self.ax.tick_params(axis='x', colors='white')
            self.ax.tick_params(axis='y', colors='white')
            self.figure.autofmt_xdate()
            self.canvas.draw()

if __name__ == "__main__":
    root = tk.Tk()
    app = BMIGUI(root)
    root.mainloop()

