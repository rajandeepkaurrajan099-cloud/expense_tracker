"""
Personal Expense Tracker  -  one file, no installs, just run it.

HOW TO RUN
  VS Code : open this file and press the Run button (top right) or F5.
  Windows : double-click the file (or right-click > Open with > Python).
  Any OS  : python expense_tracker_app.py

Click "Load demo data" on first launch to see the charts in action.
Your data is saved automatically in expenses.json next to this file.
Needs Python 3.8+ only (Tkinter is included with the standard Windows installer).
"""

import sys

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, simpledialog, ttk
except ImportError:
    print("\nThis app needs Tkinter, which your Python installation is missing.")
    print("  Windows: re-run the Python installer > Modify > tick 'tcl/tk and IDLE'.")
    print("  Ubuntu/Debian: sudo apt install python3-tk")
    print("  macOS: install Python from python.org (it includes Tkinter).\n")
    sys.exit(1)

import calendar
import csv
import json
import math
import zlib
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path

DATA_FILE = Path(__file__).resolve().with_name("expenses.json")
DATE_FORMAT = "%Y-%m-%d"
CATEGORIES = ["Food", "Transport", "Entertainment", "Bills", "Shopping", "Health", "Other"]
ALL = "All months"

# ---- warm editorial palette with calm cream surfaces and evergreen accents
FONT = "Segoe UI"
BG, CARD, BORDER = "#f3f1e9", "#fffdf8", "#dfddd2"
HEADER, ACCENT, ACCENT_DARK = "#173b35", "#e07a5f", "#c96049"
TEXT, MUTED = "#24332f", "#718079"
GOOD, WARN, BAD = "#39866a", "#d29b38", "#cf5c55"
CAT_COLORS = {"Food": "#e07a5f", "Transport": "#4f91a2", "Entertainment": "#9273b2", "Bills": "#cf5c55",
              "Shopping": "#d59a48", "Health": "#39866a", "Other": "#718079"}
EXTRA_COLORS = ["#4f91a2", "#d29b38", "#9273b2", "#78a77b", "#cf5c55", "#e07a5f"]


def color_for(category):
    return CAT_COLORS.get(category) or EXTRA_COLORS[zlib.crc32(category.encode()) % len(EXTRA_COLORS)]


def money(v):
    return f"{v:,.2f}"


# ------------------------------------------------------------------ model
@dataclass
class Expense:
    id: int
    date: str
    amount: float
    category: str
    description: str = ""

    @property
    def month(self):
        return self.date[:7]  # "YYYY-MM"


def make_expense(new_id, date_text, amount_text, category, description):
    """Validate raw form text and build an Expense (raises ValueError with a friendly message)."""
    try:
        day = datetime.strptime(date_text.strip(), DATE_FORMAT).strftime(DATE_FORMAT)
    except ValueError:
        raise ValueError(f"Invalid date '{date_text}'.\nUse YYYY-MM-DD, e.g. {date.today():%Y-%m-%d}.") from None
    try:
        amount = round(float(amount_text.replace(",", "")), 2)
    except ValueError:
        raise ValueError(f"'{amount_text}' is not a valid amount.") from None
    if amount <= 0:
        raise ValueError("Amount must be greater than zero.")
    if not math.isfinite(amount):
        raise ValueError("Amount must be a finite number.")
    category = category.strip().title()
    if not category:
        raise ValueError("Please choose or type a category.")
    return Expense(new_id, day, amount, category, description.strip())


# ---------------------------------------------------------------- storage
def load_data():
    """Return (expenses, budgets). A damaged file is kept as .corrupt, never overwritten."""
    if not DATA_FILE.exists():
        return [], {}
    try:
        raw = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        expenses = [Expense(int(d["id"]), d["date"], float(d["amount"]), d["category"], d.get("description", ""))
                    for d in raw.get("expenses", [])]
        return expenses, {k: float(v) for k, v in raw.get("budgets", {}).items()}
    except (json.JSONDecodeError, KeyError, ValueError, OSError):
        try:
            DATA_FILE.replace(DATA_FILE.with_suffix(".corrupt"))
            recovery_note = "It was renamed to expenses.corrupt."
        except OSError:
            recovery_note = "The original file could not be moved, so it has been left in place."
        messagebox.showwarning("Data file problem", "expenses.json could not be read.\n" + recovery_note +
                               "\nThe app will start with an empty list.")
        return [], {}


def save_data(expenses, budgets):
    tmp = DATA_FILE.with_suffix(".tmp")  # write-then-swap so a crash can't corrupt data
    tmp.write_text(json.dumps({"expenses": [asdict(e) for e in expenses], "budgets": budgets}, indent=2),
                   encoding="utf-8")
    tmp.replace(DATA_FILE)


def last_months(n=6):
    """The last n calendar months (YYYY-MM), oldest first, ending with this month."""
    today, out = date.today(), []
    y, m = today.year, today.month
    for _ in range(n):
        out.append(f"{y:04d}-{m:02d}")
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    return out[::-1]


# ----------------------------------------------------------------- the app
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Personal Expense Tracker")
        self.geometry("1120x700")
        self.minsize(980, 620)
        self.configure(bg=BG)
        self.expenses, self.budgets = load_data()
        self.shown, self.selected = [], None
        self.search_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready  ·  Your data is saved on this laptop")
        self.setup_style()
        self.build_header()
        self.build_cards()
        self.build_main()
        self.build_statusbar()
        self.bind_all("<Control-f>", lambda _event: self.focus_search())
        self.refresh()
        self.amount_entry.focus()

    def focus_search(self):
        """Move focus to the expense search field with Ctrl+F."""
        self.search_entry.focus_set()
        self.search_entry.select_range(0, "end")

    def build_statusbar(self):
        """Show a quiet, persistent hint and action feedback at the bottom."""
        bar = tk.Frame(self, bg=HEADER, highlightthickness=1, highlightbackground=BORDER)
        bar.pack(side="bottom", fill="x")
        tk.Frame(bar, bg=ACCENT, width=3).pack(side="left", fill="y")
        tk.Label(bar, textvariable=self.status_var, bg=HEADER, fg=MUTED,
                 font=(FONT, 9), anchor="w").pack(side="left", fill="x", expand=True, padx=12, pady=7)
        tk.Label(bar, text="LOCAL  •  JSON", bg=HEADER, fg=ACCENT,
                 font=(FONT, 8, "bold")).pack(side="right", padx=12)

    def set_status(self, message):
        self.status_var.set(message)

    def _hover_expense_row(self, event):
        """Highlight the table row under the pointer for clearer feedback."""
        item = self.tree.identify_row(event.y)
        if item == getattr(self, "_hovered_row", None):
            return
        self._clear_expense_hover()
        self._hovered_row = item
        if item and item not in self.tree.selection():
            self.tree.item(item, tags=("hover",))

    def _clear_expense_hover(self, _event=None):
        item = getattr(self, "_hovered_row", None)
        if item and self.tree.exists(item) and item not in self.tree.selection():
            values = self.tree.item(item, "values")
            try:
                index = next(i for i, expense in enumerate(self.shown)
                             if str(expense.id) == str(values[0]))
                self.tree.item(item, tags=("odd",) if index % 2 else ())
            except (IndexError, StopIteration):
                self.tree.item(item, tags=())
        self._hovered_row = None

    # ---- styling
    def setup_style(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure("TFrame", background=BG)
        s.configure("Card.TLabelframe", background=CARD, bordercolor=BORDER, relief="solid")
        s.configure("Card.TLabelframe.Label", background=CARD, foreground=ACCENT, font=(FONT, 9, "bold"))
        s.configure("TLabel", background=CARD, foreground=TEXT, font=(FONT, 10))
        s.configure("TButton", font=(FONT, 10), padding=7, background="#e9e7de", foreground=TEXT,
                    bordercolor=BORDER, focusthickness=2, focuscolor=ACCENT)
        s.map("TButton", background=[("active", "#dcd9cf"), ("pressed", "#d1cec3")],
              foreground=[("disabled", "#9b9b91")])
        s.configure("Accent.TButton", background=HEADER, foreground="white", font=(FONT, 10, "bold"),
                    padding=8, bordercolor=ACCENT)
        s.map("Accent.TButton", background=[("active", "#28564c"), ("pressed", "#102e29")])
        s.configure("TEntry", fieldbackground="#ffffff", foreground=TEXT, insertcolor=HEADER,
                    bordercolor=BORDER, padding=6)
        s.configure("TCombobox", fieldbackground="#ffffff", background="#e9e7de", foreground=TEXT,
                    arrowcolor=ACCENT, bordercolor=BORDER, padding=5)
        s.map("TCombobox", fieldbackground=[("readonly", "#ffffff")],
              foreground=[("readonly", TEXT)], selectbackground=[("readonly", "#dce9df")])
        s.configure("Treeview", rowheight=28, font=(FONT, 10), background=CARD, fieldbackground=CARD,
                    bordercolor=BORDER, foreground=TEXT)
        s.configure("Treeview.Heading", font=(FONT, 10, "bold"), background="#e9eee6", foreground=HEADER,
                    padding=8, relief="flat")
        s.map("Treeview", background=[("selected", "#d6e9dc")], foreground=[("selected", HEADER)])
        s.configure("TNotebook", background=BG, borderwidth=0, tabmargins=(3, 4, 3, 0))
        s.configure("TNotebook.Tab", font=(FONT, 10, "bold"), padding=(14, 8),
                    background="#e9e7de", foreground=MUTED)
        s.map("TNotebook.Tab", background=[("selected", CARD), ("active", "#e3eae2")],
              foreground=[("selected", ACCENT), ("active", TEXT)])

    # ---- layout
    def build_header(self):
        bar = tk.Frame(self, bg=HEADER)
        bar.pack(fill="x")
        # Decorative, gently drifting bubbles add motion without covering controls.
        self.bubble_canvas = tk.Canvas(bar, bg=HEADER, height=48, highlightthickness=0, bd=0)
        self.bubble_canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self.bubbles = [[0.68, 0.62, 9, 0.010], [0.76, 0.25, 6, 0.014],
                        [0.84, 0.78, 12, 0.008], [0.91, 0.34, 7, 0.012], [0.98, 0.70, 5, 0.016]]
        self.bubble_canvas.bind("<Button-1>", self._pop_bubble)
        self._animate_bubbles()
        tk.Label(bar, text="  Expense Tracker", bg=HEADER, fg="white", font=(FONT, 16, "bold")).pack(
            side="left", pady=12)
        tk.Label(bar, text="track  |  categorize  |  understand", bg=HEADER, fg="#d1b8ca",
                 font=(FONT, 10)).pack(side="left", padx=14)
        self.demo_btn = ttk.Button(bar, text="Load demo data", command=self.load_demo)
        self.demo_btn.pack(side="right", padx=14)

    def _animate_bubbles(self):
        if not self.winfo_exists():
            return
        canvas = self.bubble_canvas
        canvas.delete("all")
        width, height = max(canvas.winfo_width(), 1), max(canvas.winfo_height(), 1)
        for i, bubble in enumerate(self.bubbles):
            x_ratio, y_ratio, radius, speed = bubble
            y_ratio -= speed
            if y_ratio < -0.2:
                y_ratio = 1.15
            bubble[1] = y_ratio
            x = x_ratio * width
            y = y_ratio * height
            bubble_colors = ["#ffc857", "#56cfe1", "#ff9671", "#b197fc", "#72d6b2"]
            tint = bubble_colors[i % len(bubble_colors)]
            canvas.create_oval(x-radius, y-radius, x+radius, y+radius,
                               outline=tint, width=1, tags=(f"bubble{i}",))
            canvas.create_oval(x-radius*.55, y-radius*.55, x-radius*.1, y-radius*.1,
                               outline="#fff7ed", width=1, tags=(f"bubble{i}",))
        self.after(90, self._animate_bubbles)

    def _pop_bubble(self, event):
        item = self.bubble_canvas.find_closest(event.x, event.y)
        if item:
            tags = self.bubble_canvas.gettags(item[0])
            for tag in tags:
                if tag.startswith("bubble"):
                    index = int(tag[6:])
                    self.bubbles[index][1] = 1.1
                    break

    def build_cards(self):
        row = tk.Frame(self, bg=BG)
        row.pack(fill="x", padx=12, pady=(12, 4))
        self.card_vars = []
        for i, color in enumerate([ACCENT, "#ffc857", "#72d6b2", "#b197fc"]):
            card = tk.Frame(row, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
            card.grid(row=0, column=i, sticky="ew", padx=4)
            row.columnconfigure(i, weight=1)
            tk.Frame(card, bg=color, height=4).pack(fill="x")
            title, value = tk.StringVar(), tk.StringVar()
            tk.Label(card, textvariable=title, bg=CARD, fg=MUTED, font=(FONT, 9, "bold"), anchor="w").pack(
                fill="x", padx=12, pady=(8, 0))
            tk.Label(card, textvariable=value, bg=CARD, fg=TEXT, font=(FONT, 17, "bold"), anchor="w").pack(
                fill="x", padx=12, pady=(0, 10))
            self.card_vars.append((title, value))

    def build_main(self):
        main = tk.Frame(self, bg=BG)
        main.pack(fill="both", expand=True, padx=12, pady=(4, 12))
        main.columnconfigure(0, weight=5)
        main.columnconfigure(1, weight=4)
        main.rowconfigure(0, weight=1)

        # left: form + table
        left = tk.Frame(main, bg=BG)
        left.grid(row=0, column=0, sticky="nsew", padx=(4, 6))
        left.rowconfigure(1, weight=1)
        left.columnconfigure(0, weight=1)

        form = ttk.LabelFrame(left, text="ADD EXPENSE", style="Card.TLabelframe", padding=10)
        form.grid(row=0, column=0, sticky="ew")
        self.date_var = tk.StringVar(value=date.today().strftime(DATE_FORMAT))
        self.amount_var, self.desc_var = tk.StringVar(), tk.StringVar()
        self.cat_var = tk.StringVar(value=CATEGORIES[0])
        self.amount_entry = ttk.Entry(form, textvariable=self.amount_var, width=10)
        fields = [("Date (YYYY-MM-DD)", ttk.Entry(form, textvariable=self.date_var, width=13)),
                  ("Amount", self.amount_entry),
                  ("Category", ttk.Combobox(form, textvariable=self.cat_var, values=CATEGORIES, width=13)),
                  ("Description", ttk.Entry(form, textvariable=self.desc_var, width=16))]
        for col, (label, w) in enumerate(fields):
            ttk.Label(form, text=label, foreground=MUTED, font=(FONT, 9)).grid(row=0, column=col, sticky="w", padx=4)
            w.grid(row=1, column=col, padx=4, sticky="ew")
            if col != 2:
                w.bind("<Return>", lambda e: self.add_expense())
        form.columnconfigure(3, weight=1)
        ttk.Button(form, text="+ Add", style="Accent.TButton", command=self.add_expense).grid(
            row=1, column=4, padx=(8, 2))

        tools = tk.Frame(left, bg=BG)
        tools.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        tools.columnconfigure(3, weight=1)
        tk.Label(tools, text="Month", bg=BG, fg=MUTED, font=(FONT, 10, "bold")).grid(row=0, column=0, sticky="w")
        self.month_var = tk.StringVar(value=date.today().strftime("%Y-%m"))
        self.month_box = ttk.Combobox(tools, textvariable=self.month_var, state="readonly", width=12)
        self.month_box.grid(row=0, column=1, padx=(6, 10), sticky="w")
        self.month_box.bind("<<ComboboxSelected>>", lambda e: self.refresh())
        tk.Label(tools, text="Search", bg=BG, fg=MUTED, font=(FONT, 10, "bold")).grid(row=0, column=2, sticky="w")
        self.search_entry = ttk.Entry(tools, textvariable=self.search_var)
        self.search_entry.grid(row=0, column=3, padx=(6, 4), sticky="ew")
        self.search_var.trace_add("write", lambda *_: self.refresh())
        ttk.Button(tools, text="Clear", command=lambda: self.search_var.set("")).grid(row=0, column=4, padx=(0, 4))
        ttk.Button(tools, text="Edit selected", command=self.edit_selected).grid(row=1, column=2, sticky="e", pady=(6, 0))
        ttk.Button(tools, text="Delete selected", command=self.delete_selected).grid(row=1, column=3, sticky="e", pady=(6, 0))
        ttk.Button(tools, text="Export CSV", command=self.export_csv).grid(row=1, column=4, sticky="e", padx=(6, 0), pady=(6, 0))

        table = tk.Frame(left, bg=BORDER, padx=1, pady=1)
        table.grid(row=2, column=0, sticky="nsew", pady=(6, 0))
        left.rowconfigure(2, weight=1)
        left.rowconfigure(1, weight=0)
        cols = [("id", "ID", 42, "center"), ("date", "Date", 95, "center"), ("amount", "Amount", 90, "e"),
                ("category", "Category", 110, "w"), ("description", "Description", 180, "w")]
        self.tree = ttk.Treeview(table, columns=[c[0] for c in cols], show="headings", selectmode="browse")
        for key, text, width, anchor in cols:
            self.tree.heading(key, text=text)
            self.tree.column(key, width=width, anchor=anchor, stretch=(key == "description"))
        # Keep every table row on the same light surface for consistent contrast.
        self.tree.tag_configure("odd", background=CARD, foreground=TEXT)
        self.tree.tag_configure("hover", background="#e6efe5", foreground=HEADER)
        scroll = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)
        self.tree.bind("<Delete>", lambda e: self.delete_selected())
        self.tree.bind("<Double-1>", lambda e: self.edit_selected())
        self.tree.bind("<Motion>", self._hover_expense_row)
        self.tree.bind("<Leave>", self._clear_expense_hover)

        # right: charts
        tabs = ttk.Notebook(main)
        tabs.grid(row=0, column=1, sticky="nsew", padx=(6, 4))
        pie_tab, trend_tab = tk.Frame(tabs, bg=CARD), tk.Frame(tabs, bg=CARD)
        tabs.add(pie_tab, text="  Breakdown  ")
        tabs.add(trend_tab, text="  Monthly trend  ")

        btns = tk.Frame(pie_tab, bg=CARD)
        btns.pack(side="bottom", fill="x", padx=8, pady=6)
        ttk.Button(btns, text="Set / change a budget", command=self.set_budget).pack(side="left", expand=True, fill="x")
        ttk.Button(btns, text="Remove a budget", command=self.remove_budget).pack(side="left", expand=True, fill="x",
                                                                                  padx=(6, 0))
        self.pie = tk.Canvas(pie_tab, bg=CARD, highlightthickness=0)
        sb = ttk.Scrollbar(pie_tab, orient="vertical", command=self.pie.yview)
        self.pie.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.pie.pack(side="left", fill="both", expand=True)
        self.pie.bind("<Configure>", lambda e: self.draw_breakdown())
        self.pie.bind("<MouseWheel>", lambda e: self.pie.yview_scroll(-1 * (e.delta // 120), "units"))

        self.trend = tk.Canvas(trend_tab, bg=CARD, highlightthickness=0)
        self.trend.pack(fill="both", expand=True)
        self.trend.bind("<Configure>", lambda e: self.draw_trend())

    # ---- actions
    def add_expense(self):
        next_id = max((e.id for e in self.expenses), default=0) + 1
        try:
            e = make_expense(next_id, self.date_var.get(), self.amount_var.get(),
                             self.cat_var.get(), self.desc_var.get())
        except ValueError as exc:
            messagebox.showerror("Invalid input", str(exc))
            return
        self.expenses.append(e)
        if not self.persist():
            self.expenses.remove(e)
            return
        self.amount_var.set("")
        self.desc_var.set("")
        self.month_var.set(e.month)
        self.refresh()
        self.set_status(f"Saved {e.category} expense  ·  {money(e.amount)}  ·  {e.date}")
        self.amount_entry.focus()
        limit = self.budgets.get(e.category)
        spent = sum(x.amount for x in self.expenses if x.month == e.month and x.category == e.category)
        if limit is not None and spent > limit:
            messagebox.showwarning("Over budget", f"{e.category} is over budget for {e.month}:\n"
                                                  f"{money(spent)} spent of {money(limit)}.")

    def delete_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Delete", "Click an expense in the table first.")
            return
        exp_id = int(self.tree.item(sel[0])["values"][0])
        if messagebox.askyesno("Delete", "Delete the selected expense?"):
            previous = self.expenses
            self.expenses = [e for e in previous if e.id != exp_id]
            if not self.persist():
                self.expenses = previous
                return
            self.refresh()
            self.set_status("Expense deleted")

    def edit_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Edit", "Select an expense in the table first.")
            return
        exp_id = int(self.tree.item(sel[0])["values"][0])
        original = next((expense for expense in self.expenses if expense.id == exp_id), None)
        if original is None:
            messagebox.showerror("Edit", "That expense could not be found. Refresh the list and try again.")
            return

        dialog = tk.Toplevel(self)
        dialog.title("Edit expense")
        dialog.configure(bg=BG)
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        tk.Label(dialog, text="Update expense details", bg=BG, fg=HEADER,
                 font=(FONT, 14, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(14, 8))
        date_var = tk.StringVar(value=original.date)
        amount_var = tk.StringVar(value=f"{original.amount:.2f}")
        category_var = tk.StringVar(value=original.category)
        description_var = tk.StringVar(value=original.description)
        fields = [("Date (YYYY-MM-DD)", ttk.Entry(dialog, textvariable=date_var, width=28)),
                  ("Amount", ttk.Entry(dialog, textvariable=amount_var, width=28)),
                  ("Category", ttk.Combobox(dialog, textvariable=category_var, values=CATEGORIES, width=26)),
                  ("Description", ttk.Entry(dialog, textvariable=description_var, width=28))]
        for row, (label, widget) in enumerate(fields, start=1):
            ttk.Label(dialog, text=label).grid(row=row, column=0, sticky="w", padx=16, pady=6)
            widget.grid(row=row, column=1, sticky="ew", padx=16, pady=6)

        def save_changes():
            try:
                updated = make_expense(exp_id, date_var.get(), amount_var.get(),
                                       category_var.get(), description_var.get())
            except ValueError as exc:
                messagebox.showerror("Invalid input", str(exc), parent=dialog)
                return
            index = self.expenses.index(original)
            self.expenses[index] = updated
            if not self.persist():
                self.expenses[index] = original
                return
            dialog.destroy()
            self.month_var.set(updated.month)
            self.refresh()
            self.set_status("Expense changes saved")

        ttk.Button(dialog, text="Save changes", style="Accent.TButton", command=save_changes).grid(
            row=5, column=0, columnspan=2, pady=(10, 16))
        dialog.bind("<Return>", lambda _event: save_changes())

    def persist(self):
        """Save current data and show a helpful message if the folder is read-only."""
        try:
            save_data(self.expenses, self.budgets)
            return True
        except OSError as exc:
            messagebox.showerror("Could not save data",
                                 f"The app could not save expenses.json. Check that the folder is writable.\n\n{exc}",
                                 parent=self)
            return False

    def set_budget(self):
        cat = simpledialog.askstring("Budget", "Category (e.g. Food):", parent=self)
        if not cat or not cat.strip():
            return
        text = simpledialog.askstring("Budget", f"Monthly limit for {cat.strip().title()}:", parent=self)
        if text is None:
            return
        try:
            limit = round(float(text.replace(",", "")), 2)
            if limit <= 0 or not math.isfinite(limit):
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid amount", "Enter a positive number, e.g. 500.")
            return
        key = cat.strip().title()
        previous = self.budgets.get(key)
        self.budgets[key] = limit
        if not self.persist():
            if previous is None:
                self.budgets.pop(key, None)
            else:
                self.budgets[key] = previous
            return
        self.refresh()
        self.set_status(f"Monthly category limit saved for {key}")

    def remove_budget(self):
        if not self.budgets:
            messagebox.showinfo("Budgets", "No budgets set yet.")
            return
        cat = simpledialog.askstring("Remove budget", "Which category?\n" + ", ".join(sorted(self.budgets)),
                                     parent=self)
        if cat:
            key = cat.strip().title()
            previous = self.budgets.pop(key, None)
            if previous is not None:
                if not self.persist():
                    self.budgets[key] = previous
                    return
                self.refresh()
                self.set_status(f"Budget removed for {key}")

    def export_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV file", "*.csv")],
                                            initialfile="expenses.csv")
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=["id", "date", "amount", "category", "description"])
                writer.writeheader()
                writer.writerows(asdict(e) for e in sorted(self.expenses, key=lambda x: (x.date, x.id)))
        except OSError as exc:
            messagebox.showerror("Export failed", f"The CSV could not be written.\n\n{exc}", parent=self)
            return
        messagebox.showinfo("Export", f"Exported {len(self.expenses)} expenses to:\n{path}")
        self.set_status(f"CSV export complete  ·  {len(self.expenses)} expense(s)")

    def load_demo(self):
        """Fill the app with 3 months of sample data so the charts have something to show."""
        if self.expenses:
            return
        previous_expenses = self.expenses.copy()
        previous_budgets = self.budgets.copy()
        template = [(2, 420, "Food", "Groceries"), (4, 150, "Transport", "Auto fare"),
                    (7, 899, "Entertainment", "Movie night"), (9, 1200, "Bills", "Electricity bill"),
                    (12, 640, "Shopping", "New shirt"), (15, 380, "Food", "Dinner out"),
                    (18, 220, "Health", "Pharmacy"), (21, 300, "Transport", "Fuel"),
                    (24, 520, "Food", "Groceries"), (27, 450, "Entertainment", "Games")]
        today, next_id = date.today(), 1
        for back, factor in ((2, 0.9), (1, 1.15), (0, 1.0)):
            y, m = today.year, today.month - back
            if m < 1:
                y, m = y - 1, m + 12
            for day, amount, cat, desc in template:
                day = min(day, today.day) if back == 0 else min(day, 28)
                self.expenses.append(Expense(next_id, f"{y:04d}-{m:02d}-{day:02d}", round(amount * factor), cat, desc))
                next_id += 1
        self.budgets = {"Food": 1200.0, "Entertainment": 1500.0}
        if not self.persist():
            self.expenses = previous_expenses
            self.budgets = previous_budgets
            return
        self.month_var.set(today.strftime("%Y-%m"))
        self.refresh()
        self.set_status("Demo data loaded  ·  Explore the charts and monthly trend")

    def select_month(self, ym):
        self.month_var.set(ym)
        self.refresh()

    # ---- display
    def refresh(self):
        current = date.today().strftime("%Y-%m")
        self.month_box["values"] = [ALL] + sorted({e.month for e in self.expenses} | {current}, reverse=True)
        month = self.month_var.get()
        self.selected = None if month == ALL else month
        query = self.search_var.get().strip().casefold()
        self.shown = sorted((e for e in self.expenses
                             if (self.selected is None or e.month == self.selected)
                             and (not query or query in " ".join((str(e.id), e.date, money(e.amount),
                                                                    e.category, e.description)).casefold())),
                            key=lambda e: (e.date, e.id))
        self.tree.delete(*self.tree.get_children())
        for i, e in enumerate(self.shown):
            self.tree.insert("", "end", values=(e.id, e.date, money(e.amount), e.category, e.description),
                             tags=("odd",) if i % 2 else ())
        self.demo_btn.configure(state="disabled" if self.expenses else "normal")
        self.update_cards()
        self.draw_breakdown()
        self.draw_trend()
        if hasattr(self, "status_var"):
            self.set_status(f"Showing {len(self.shown)} of {len(self.expenses)} expense(s)  ·  Ctrl+F to search")

    def totals(self):
        t = defaultdict(float)
        for e in self.shown:
            t[e.category] += e.amount
        return t

    def update_cards(self):
        totals, total = self.totals(), sum(e.amount for e in self.shown)
        period = "all time" if self.selected is None else datetime.strptime(self.selected, "%Y-%m").strftime("%B %Y")
        if totals:
            top = max(totals, key=totals.get)
            top_text = f"{top}  ({totals[top] / total * 100:.0f}%)"
        else:
            top_text = "-"
        if self.selected is None:
            avg_title, avg = "AVERAGE PER EXPENSE", (total / len(self.shown) if self.shown else 0)
        else:
            y, m = map(int, self.selected.split("-"))
            days = date.today().day if self.selected == date.today().strftime("%Y-%m") else calendar.monthrange(y, m)[1]
            avg_title, avg = "DAILY AVERAGE", total / days
        cards = [(f"TOTAL SPENT  -  {period.upper()}", money(total)), ("EXPENSES RECORDED", str(len(self.shown))),
                 ("TOP CATEGORY", top_text), (avg_title, money(avg))]
        for (title_var, value_var), (title, value) in zip(self.card_vars, cards):
            title_var.set(title)
            value_var.set(value)

    def draw_breakdown(self):
        c = self.pie
        c.delete("all")
        W = max(c.winfo_width(), 300)
        totals = self.totals()
        if not totals:
            c.create_text(W / 2, 90, text="No expenses for this period yet.", fill=MUTED, font=(FONT, 11))
            if not self.expenses:
                c.create_text(W / 2, 120, text='Add one, or click "Load demo data".', fill=MUTED, font=(FONT, 10))
            c.configure(scrollregion=(0, 0, W, 10))
            return
        grand, size, top = sum(totals.values()), 190, 14
        cx, cy = W / 2, top + 190 / 2
        box = (cx - size / 2, top, cx + size / 2, top + size)
        start = 90
        for cat, amount in sorted(totals.items(), key=lambda kv: kv[1], reverse=True):
            extent = -359.99 if len(totals) == 1 else -amount / grand * 360
            c.create_arc(box, start=start, extent=extent, fill=color_for(cat), outline=CARD, width=2, style="pieslice")
            start += extent
        r = size * 0.30
        c.create_oval(cx - r - 20, cy - r - 20, cx + r + 20, cy + r + 20, fill=CARD, outline=CARD)
        c.create_text(cx, cy - 10, text=f"{grand:,.0f}", fill=TEXT, font=(FONT, 18, "bold"))
        c.create_text(cx, cy + 14, text="total spent", fill=MUTED, font=(FONT, 9))

        y = top + size + 22
        for cat, amount in sorted(totals.items(), key=lambda kv: kv[1], reverse=True):
            c.create_rectangle(14, y + 3, 26, y + 15, fill=color_for(cat), width=0)
            c.create_text(34, y, anchor="nw", text=cat, fill=TEXT, font=(FONT, 10, "bold"))
            c.create_text(W - 14, y, anchor="ne", text=f"{money(amount)}   {amount / grand * 100:.0f}%",
                          fill=TEXT, font=(FONT, 10))
            y += 24
            limit = self.budgets.get(cat) if self.selected else None
            if limit:
                ratio = amount / limit
                col = BAD if ratio > 1 else WARN if ratio >= 0.8 else GOOD
                c.create_rectangle(34, y, W - 14, y + 7, fill="#44394d", width=0)
                c.create_rectangle(34, y, 34 + (W - 48) * min(ratio, 1), y + 7, fill=col, width=0)
                note = (f"Over budget by {money(amount - limit)}" if ratio > 1
                        else f"{money(limit - amount)} left of {money(limit)}")
                c.create_text(34, y + 10, anchor="nw", text=note, fill=col if ratio >= 0.8 else MUTED, font=(FONT, 8))
                y += 30
            y += 6
        c.configure(scrollregion=(0, 0, W, max(y + 6, c.winfo_height())))

    def draw_trend(self):
        c = self.trend
        c.delete("all")
        W, H = max(c.winfo_width(), 320), max(c.winfo_height(), 260)
        months = last_months(6)
        sums = {m: sum(e.amount for e in self.expenses if e.month == m) for m in months}
        peak = max(sums.values()) or 1
        left, right, top, bottom = 16, 16, 52, 34
        c.create_text(left, 14, anchor="nw", text="Last 6 months", fill=TEXT, font=(FONT, 12, "bold"))
        c.create_text(left, 34, anchor="nw", text="Click a bar to view that month", fill=MUTED, font=(FONT, 9))
        plot_h = H - top - bottom
        for frac in (0, 0.5, 1):
            gy = top + plot_h * (1 - frac)
            c.create_line(left, gy, W - right, gy, fill="#44394d")
        slot = (W - left - right) / len(months)
        for i, m in enumerate(months):
            x0, x1 = left + i * slot + slot * 0.18, left + (i + 1) * slot - slot * 0.18
            h = plot_h * sums[m] / peak
            tag = f"bar{i}"
            fill = ACCENT if m == self.selected else "#705f7b"
            c.create_rectangle(x0, top + plot_h - h, x1, top + plot_h, fill=fill, width=0, tags=(tag,))
            if sums[m]:
                c.create_text((x0 + x1) / 2, top + plot_h - h - 4, anchor="s", text=f"{sums[m]:,.0f}",
                              fill=TEXT, font=(FONT, 9, "bold" if m == self.selected else "normal"))
            c.create_text((x0 + x1) / 2, top + plot_h + 8, anchor="n",
                          text=calendar.month_abbr[int(m[5:])], fill=TEXT if m == self.selected else MUTED,
                          font=(FONT, 10, "bold" if m == self.selected else "normal"))
            c.create_rectangle(x0, top, x1, top + plot_h + 28, fill="", outline="", tags=(tag,))  # bigger click area
            c.tag_bind(tag, "<Button-1>", lambda e, ym=m: self.select_month(ym))
            c.tag_bind(tag, "<Enter>", lambda e: c.configure(cursor="hand2"))
            c.tag_bind(tag, "<Leave>", lambda e: c.configure(cursor=""))


def main():
    if sys.platform == "win32":  # crisp text on high-DPI Windows screens
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
    App().mainloop()


if __name__ == "__main__":
    main()
