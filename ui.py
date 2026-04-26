import random
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox

try:
    from solver import solve
except ImportError:
    solve = None

try:
    from storage import (
        init_db,
        save_record,
        load_all_records,
        load_record_by_name,
        delete_record_by_name,
    )
except ImportError:
    init_db = None
    save_record = None
    load_all_records = None
    load_record_by_name = None
    delete_record_by_name = None


class OptimalSamplesApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("An Optimal Samples Selection System")
        self.root.geometry("1280x760")
        self.root.minsize(1180, 700)

        self.record_names = []
        self.current_result_pages = []
        self.current_page_index = 0
        self.main_page_state = None
        self.last_solver_result = None

        if init_db is not None:
            init_db()

        self._build_main_page()

    def run(self):
        self.root.mainloop()

    def _clear_root(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def _make_button(self, parent, text, command, pady=8):
        button = ttk.Button(parent, text=text, command=command, width=16)
        button.pack(pady=pady)
        return button

    def copy_selected_text(self, event):
        widget = event.widget
        try:
            selected_text = widget.selection_get()
        except tk.TclError:
            return "break"

        self.root.clipboard_clear()
        self.root.clipboard_append(selected_text)
        return "break"

    def bind_copy_shortcuts(self):
        for name in ("values_text", "results_text", "record_detail_text"):
            widget = getattr(self, name, None)
            if widget is not None and widget.winfo_exists():
                widget.bind("<Control-c>", self.copy_selected_text)
                widget.bind("<Control-C>", self.copy_selected_text)

    def _sync_at_least_from_s(self, *args):
        if hasattr(self, "at_least_var") and hasattr(self, "s_var"):
            self.at_least_var.set(self.s_var.get().strip())

    def set_values_content(self, text):
        self.values_text.config(state="normal")
        self.values_text.delete("1.0", tk.END)
        self.values_text.insert("1.0", text)
        self.values_text.config(state="disabled")

    def append_values_line(self, text):
        self.values_text.config(state="normal")
        self.values_text.insert(tk.END, text)
        self.values_text.config(state="disabled")

    def save_main_page_state(self):
        if not hasattr(self, "m_var"):
            return

        manual_values = []
        if hasattr(self, "manual_entries"):
            manual_values = [entry.get() for entry in self.manual_entries]

        values_content = ""
        if hasattr(self, "values_text"):
            self.values_text.config(state="normal")
            values_content = self.values_text.get("1.0", tk.END)
            self.values_text.config(state="disabled")

        results_content = ""
        if hasattr(self, "results_text"):
            results_content = self.results_text.get("1.0", tk.END)

        self.main_page_state = {
            "m": self.m_var.get(),
            "n": self.n_var.get(),
            "k": self.k_var.get(),
            "j": self.j_var.get(),
            "s": self.s_var.get(),
            "at_least": self.at_least_var.get(),
            "mode": self.mode_var.get(),
            "manual_values": manual_values,
            "values_content": values_content,
            "results_content": results_content,
            "current_result_pages": self.current_result_pages,
            "current_page_index": self.current_page_index,
            "last_solver_result": self.last_solver_result,
        }

    def restore_main_page_state(self):
        if not self.main_page_state:
            return

        state = self.main_page_state

        self.m_var.set(state.get("m", ""))
        self.n_var.set(state.get("n", ""))
        self.k_var.set(state.get("k", ""))
        self.j_var.set(state.get("j", ""))
        self.s_var.set(state.get("s", ""))
        self.mode_var.set(state.get("mode", "random"))
        self._sync_at_least_from_s()

        for entry in self.manual_entries:
            entry.delete(0, tk.END)

        for entry, value in zip(self.manual_entries, state.get("manual_values", [])):
            entry.insert(0, value)

        self.set_values_content(state.get("values_content", ""))

        self.results_text.delete("1.0", tk.END)
        self.results_text.insert("1.0", state.get("results_content", ""))

        self.current_result_pages = state.get("current_result_pages", [])
        self.current_page_index = state.get("current_page_index", 0)
        self.last_solver_result = state.get("last_solver_result")

    def open_history_page(self):
        self.save_main_page_state()
        self._build_database_page()

    def go_back_to_main_page(self):
        saved_state = self.main_page_state
        self._build_main_page()
        self.main_page_state = saved_state
        self.restore_main_page_state()

    def _build_main_page(self):
        self._clear_root()

        self.m_var = tk.StringVar()
        self.n_var = tk.StringVar()
        self.k_var = tk.StringVar()
        self.j_var = tk.StringVar()
        self.s_var = tk.StringVar()
        self.at_least_var = tk.StringVar()
        self.mode_var = tk.StringVar(value="random")

        self.s_var.trace_add("write", self._sync_at_least_from_s)

        container = ttk.Frame(self.root, padding=12)
        container.pack(fill="both", expand=True)

        container.columnconfigure(0, weight=1)
        container.rowconfigure(2, weight=1)

        title = ttk.Label(
            container,
            text="An Optimal Samples Selection System",
            font=("Arial", 24, "bold")
        )
        title.grid(row=0, column=0, pady=(5, 15), sticky="n")

        param_frame = ttk.LabelFrame(
            container,
            text="Please input the following parameters",
            padding=14
        )
        param_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))

        ttk.Label(param_frame, text="m (45≤m≤54)").grid(row=0, column=0, padx=(10, 6), pady=8, sticky="w")
        ttk.Entry(param_frame, textvariable=self.m_var, width=12).grid(row=0, column=1, padx=(0, 20), pady=8, sticky="w")

        ttk.Label(param_frame, text="n (7≤n≤25)").grid(row=0, column=2, padx=(10, 6), pady=8, sticky="w")
        ttk.Entry(param_frame, textvariable=self.n_var, width=12).grid(row=0, column=3, padx=(0, 20), pady=8, sticky="w")

        ttk.Label(param_frame, text="k (4≤k≤7)").grid(row=1, column=0, padx=(10, 6), pady=8, sticky="w")
        ttk.Entry(param_frame, textvariable=self.k_var, width=12).grid(row=1, column=1, padx=(0, 20), pady=8, sticky="w")

        ttk.Label(param_frame, text="j (s≤j≤k)").grid(row=1, column=2, padx=(10, 6), pady=8, sticky="w")
        ttk.Entry(param_frame, textvariable=self.j_var, width=12).grid(row=1, column=3, padx=(0, 20), pady=8, sticky="w")

        ttk.Label(param_frame, text="s (3≤s≤7)").grid(row=2, column=0, padx=(10, 6), pady=8, sticky="w")
        ttk.Entry(param_frame, textvariable=self.s_var, width=12).grid(row=2, column=1, padx=(0, 20), pady=8, sticky="w")

        ttk.Label(param_frame, text="at least").grid(row=2, column=2, padx=(10, 6), pady=8, sticky="w")
        ttk.Entry(param_frame, textvariable=self.at_least_var, width=8, state="readonly").grid(row=2, column=3, padx=(0, 6), pady=8, sticky="w")
        ttk.Label(param_frame, text="common samples").grid(row=2, column=4, padx=(4, 0), pady=8, sticky="w")

        self._sync_at_least_from_s()

        ttk.Radiobutton(param_frame, text="Random n", variable=self.mode_var, value="random").grid(
            row=3, column=0, padx=(10, 10), pady=(10, 0), sticky="w"
        )
        ttk.Radiobutton(param_frame, text="Input n", variable=self.mode_var, value="manual").grid(
            row=3, column=1, padx=(0, 10), pady=(10, 0), sticky="w"
        )

        middle_frame = ttk.Frame(container)
        middle_frame.grid(row=2, column=0, sticky="nsew", pady=(0, 8))
        middle_frame.columnconfigure(0, weight=1)
        middle_frame.columnconfigure(1, weight=1)
        middle_frame.columnconfigure(2, weight=0)
        middle_frame.rowconfigure(0, weight=1)
        middle_frame.grid_propagate(False)
        middle_frame.configure(height=340)

        values_frame = ttk.LabelFrame(middle_frame, text="values input", padding=8)
        values_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        self.values_text = tk.Text(values_frame, font=("Consolas", 11), wrap="none", height=14)
        self.values_text.pack(side="left", fill="both", expand=True)

        values_scroll = ttk.Scrollbar(values_frame, orient="vertical", command=self.values_text.yview)
        values_scroll.pack(side="right", fill="y")
        self.values_text.config(yscrollcommand=values_scroll.set)
        self.values_text.config(state="disabled")

        results_frame = ttk.LabelFrame(middle_frame, text="results", padding=8)
        results_frame.grid(row=0, column=1, sticky="nsew")

        self.results_text = tk.Text(results_frame, font=("Consolas", 11), wrap="word", height=14)
        self.results_text.pack(side="left", fill="both", expand=True)

        results_scroll = ttk.Scrollbar(results_frame, orient="vertical", command=self.results_text.yview)
        results_scroll.pack(side="right", fill="y")
        self.results_text.config(yscrollcommand=results_scroll.set)

        button_frame = ttk.Frame(middle_frame, width=160, height=340)
        button_frame.grid(row=0, column=2, sticky="ns", padx=(12, 0))
        button_frame.grid_propagate(False)

        self._make_button(button_frame, "Execute", self.execute_action, pady=10)
        self._make_button(button_frame, "Store", self.store_action, pady=8)
        self._make_button(button_frame, "Clear", self.clear_action, pady=8)
        ttk.Label(button_frame, text="").pack(pady=8)
        self._make_button(button_frame, "Print", self.print_action, pady=8)
        self._make_button(button_frame, "Next", self.next_action, pady=8)
        self._make_button(button_frame, "History", self.open_history_page, pady=8)

        bottom_frame = ttk.LabelFrame(container, text="user input", padding=10)
        bottom_frame.grid(row=3, column=0, sticky="ew", pady=(8, 0))

        input_canvas = tk.Canvas(bottom_frame, height=95, highlightthickness=0)
        input_scrollbar = ttk.Scrollbar(bottom_frame, orient="horizontal", command=input_canvas.xview)
        input_canvas.configure(xscrollcommand=input_scrollbar.set)

        input_canvas.pack(fill="x", expand=True, side="top")
        input_scrollbar.pack(fill="x", side="bottom")

        input_inner = ttk.Frame(input_canvas)
        input_canvas.create_window((0, 0), window=input_inner, anchor="nw")

        self.manual_entries = []
        for i in range(25):
            cell = ttk.Frame(input_inner)
            cell.grid(row=0, column=i, padx=8, pady=6)

            entry = ttk.Entry(cell, width=4, justify="center")
            entry.pack()

            ttk.Label(cell, text=str(i + 1), font=("Arial", 8)).pack(pady=(2, 0))
            self.manual_entries.append(entry)

        input_inner.update_idletasks()
        input_canvas.configure(scrollregion=input_canvas.bbox("all"))

        self.bind_copy_shortcuts()

    def _build_database_page(self):
        self._clear_root()

        container = ttk.Frame(self.root, padding=12)
        container.pack(fill="both", expand=True)

        title = ttk.Label(
            container,
            text="An Optimal Samples Selection System\nDatabase Resource",
            font=("Arial", 22, "bold"),
            justify="center"
        )
        title.pack(pady=(5, 15))

        body = ttk.Frame(container)
        body.pack(fill="both", expand=True)

        list_frame = ttk.LabelFrame(body, text="Saved Records", padding=8)
        list_frame.pack(side="left", fill="y", padx=(0, 10))

        self.record_listbox = tk.Listbox(list_frame, width=36, height=22, font=("Consolas", 11))
        self.record_listbox.pack(side="left", fill="y")

        list_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.record_listbox.yview)
        list_scroll.pack(side="right", fill="y")
        self.record_listbox.config(yscrollcommand=list_scroll.set)

        self.refresh_record_listbox()

        detail_frame = ttk.LabelFrame(body, text="Record Details", padding=8)
        detail_frame.pack(side="left", fill="both", expand=True)

        self.record_detail_text = tk.Text(detail_frame, font=("Consolas", 11), wrap="word")
        self.record_detail_text.pack(side="left", fill="both", expand=True)

        detail_scroll = ttk.Scrollbar(detail_frame, orient="vertical", command=self.record_detail_text.yview)
        detail_scroll.pack(side="right", fill="y")
        self.record_detail_text.config(yscrollcommand=detail_scroll.set)

        right_buttons = ttk.Frame(body, width=160)
        right_buttons.pack(side="right", fill="y", padx=(12, 0))
        right_buttons.pack_propagate(False)

        self._make_button(right_buttons, "Display", self.display_record, pady=16)
        self._make_button(right_buttons, "Delete", self.delete_record, pady=10)
        ttk.Label(right_buttons, text="").pack(pady=20)
        self._make_button(right_buttons, "Back", self.go_back_to_main_page, pady=10)
        self._make_button(right_buttons, "Print", self.print_action, pady=10)

        self.bind_copy_shortcuts()

    def refresh_record_listbox(self):
        if not hasattr(self, "record_listbox"):
            return

        self.record_listbox.delete(0, tk.END)

        if load_all_records is None:
            return

        self.record_names = load_all_records()
        for name in self.record_names:
            self.record_listbox.insert(tk.END, name)

    def get_validated_parameters(self):
        try:
            m = int(self.m_var.get().strip())
            n = int(self.n_var.get().strip())
            k = int(self.k_var.get().strip())
            j = int(self.j_var.get().strip())
            s = int(self.s_var.get().strip())
        except ValueError:
            messagebox.showerror("Input Error", "m, n, k, j, s must all be integers.")
            return None

        if not (45 <= m <= 54):
            messagebox.showerror("Input Error", "m must be between 45 and 54.")
            return None
        if not (7 <= n <= 25):
            messagebox.showerror("Input Error", "n must be between 7 and 25.")
            return None
        if not (4 <= k <= 7):
            messagebox.showerror("Input Error", "k must be between 4 and 7.")
            return None
        if not (3 <= s <= 7):
            messagebox.showerror("Input Error", "s must be between 3 and 7.")
            return None
        if not (s <= j <= k):
            messagebox.showerror("Input Error", "j must satisfy s ≤ j ≤ k.")
            return None
        if n < k:
            messagebox.showerror("Input Error", "n must be greater than or equal to k.")
            return None

        return m, n, k, j, s

    def get_selected_numbers(self, m, n):
        if self.mode_var.get() == "random":
            return sorted(random.sample(range(1, m + 1), n))

        manual_values = []
        for entry in self.manual_entries:
            value = entry.get().strip()
            if value:
                manual_values.append(value)

        if len(manual_values) != n:
            messagebox.showerror("Input Error", f"You must enter exactly {n} numbers for manual input.")
            return None

        try:
            numbers = [int(v) for v in manual_values]
        except ValueError:
            messagebox.showerror("Input Error", "Manual input must contain integers only.")
            return None

        if len(set(numbers)) != len(numbers):
            messagebox.showerror("Input Error", "Manual input contains duplicate numbers.")
            return None

        if any(num < 1 or num > m for num in numbers):
            messagebox.showerror("Input Error", f"All manual input numbers must be between 1 and {m}.")
            return None

        return sorted(numbers)

    def paginate_groups(self, groups, page_size=8):
        if not groups:
            return [[]]

        pages = []
        for i in range(0, len(groups), page_size):
            pages.append(groups[i:i + page_size])
        return pages

    def format_results_header(self, result):
        lines = []
        total_pages = len(self.current_result_pages) if self.current_result_pages else 1
        lines.append(f"Results Page {self.current_page_index + 1}/{total_pages}")
        lines.append("-" * 42)
        lines.append(f"Status: {result.get('status', '')}")
        lines.append(f"Message: {result.get('message', '')}")
        lines.append(f"Mode: {result.get('mode', '')}")
        lines.append(f"Valid Coverage: {result.get('is_valid', False)}")
        lines.append(f"Group Count: {result.get('group_count', 0)}")
        lines.append(f"Runtime: {result.get('runtime_ms', 0)} ms")
        lines.append(f"Target Count: {result.get('target_count', 0)}")
        lines.append(f"Candidates Used: {result.get('candidate_count_used', 0)}")
        lines.append(f"Candidates Total: {result.get('candidate_count_total', 0)}")
        lines.append(f"Uncovered Targets: {result.get('uncovered_target_count', 0)}")
        lines.append("-" * 42)
        return "\n".join(lines) + "\n"

    def build_record_name(self, result):
        params = result.get("input", {})
        m = params.get("m", "")
        n = params.get("n", "")
        k = params.get("k", "")
        j = params.get("j", "")
        s = params.get("s", "")
        group_count = result.get("group_count", 0)
        stamp = datetime.now().strftime("%H%M%S%f")[:-3]

        return f"{m}-{n}-{k}-{j}-{s}-{stamp}-{group_count}"

    def build_record_content(self, result):
        params = result.get("input", {})
        saved_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        lines = []
        lines.append(f"Saved At: {saved_at}")
        lines.append(f"Status: {result.get('status', '')}")
        lines.append(f"Message: {result.get('message', '')}")
        lines.append("-" * 42)
        lines.append(f"m = {params.get('m', '')}")
        lines.append(f"n = {params.get('n', '')}")
        lines.append(f"k = {params.get('k', '')}")
        lines.append(f"j = {params.get('j', '')}")
        lines.append(f"s = {params.get('s', '')}")
        lines.append(f"Runtime: {result.get('runtime_ms', 0)} ms")
        lines.append(f"Result Count: {result.get('group_count', 0)}")
        lines.append(f"Target Count: {result.get('target_count', 0)}")
        lines.append(f"Candidates Used: {result.get('candidate_count_used', 0)}")
        lines.append(f"Candidates Total: {result.get('candidate_count_total', 0)}")
        lines.append(f"Mode: {result.get('mode', '')}")
        lines.append(f"Valid Coverage: {result.get('is_valid', False)}")
        lines.append(f"Uncovered Targets: {result.get('uncovered_target_count', 0)}")
        lines.append("-" * 42)
        lines.append(f"Selected Numbers: {result.get('samples', [])}")
        lines.append("-" * 42)
        lines.append("Selected Groups:")

        for idx, group in enumerate(result.get("selected_groups", []), start=1):
            lines.append(f"{idx}. {tuple(group)}")

        return "\n".join(lines)

    def execute_action(self):
        if solve is None:
            messagebox.showerror(
                "Import Error",
                "Cannot import solve() from solver.py.\nPlease confirm solver.py is in the project folder."
            )
            return

        validated = self.get_validated_parameters()
        if not validated:
            return

        m, n, k, j, s = validated
        selected_numbers = self.get_selected_numbers(m, n)
        if selected_numbers is None:
            return

        self.set_values_content("")
        self.results_text.delete("1.0", tk.END)

        for idx, value in enumerate(selected_numbers, start=1):
            self.append_values_line(f"{idx}th #   {value}\n")

        try:
            result = solve(
                samples=selected_numbers,
                m=m,
                n=n,
                k=k,
                j=j,
                s=s,
                max_candidates=200000,
                seed=42,
                attempts=3,
            )
        except Exception as exc:
            messagebox.showerror("Execute Error", f"Solver execution failed:\n{exc}")
            return

        self.last_solver_result = result

        status = result.get("status", "error")
        if status == "error":
            messagebox.showerror("Solver Error", result.get("message", "Unknown solver error."))
            return

        selected_groups = result.get("selected_groups", [])
        self.current_result_pages = self.paginate_groups(selected_groups, page_size=8)
        self.current_page_index = 0
        self.show_current_result_page()
        self.save_main_page_state()

        if status == "partial":
            messagebox.showwarning(
                "Partial Result",
                result.get("message", "Incomplete coverage returned by solver.")
            )

    def show_current_result_page(self):
        self.results_text.delete("1.0", tk.END)

        if not self.last_solver_result:
            self.results_text.insert(tk.END, "No results available.\n")
            return

        header = self.format_results_header(self.last_solver_result)
        self.results_text.insert(tk.END, header)

        page_groups = []
        if self.current_result_pages:
            page_groups = self.current_result_pages[self.current_page_index]

        if not page_groups:
            self.results_text.insert(tk.END, "(No selected groups)\n")
            return

        start_index = self.current_page_index * 8 + 1
        for offset, group in enumerate(page_groups):
            self.results_text.insert(tk.END, f"{start_index + offset}. {tuple(group)}\n")

    def next_action(self):
        if not self.current_result_pages:
            messagebox.showinfo("Next", "No result pages available.")
            return

        self.current_page_index = (self.current_page_index + 1) % len(self.current_result_pages)
        self.show_current_result_page()
        self.save_main_page_state()

    def store_action(self):
        if save_record is None:
            messagebox.showerror("Store Error", "Cannot import storage functions from storage.py.")
            return

        if not self.last_solver_result:
            messagebox.showwarning("Store", "No solver result to store.")
            return

        status = self.last_solver_result.get("status", "")
        if status == "error":
            messagebox.showwarning("Store", "Current result is invalid and cannot be stored.")
            return

        record_name = self.build_record_name(self.last_solver_result)
        record_content = self.build_record_content(self.last_solver_result)

        try:
            save_record(record_name, record_content)
        except Exception as exc:
            messagebox.showerror("Store Error", f"Failed to save record:\n{exc}")
            return

        self.save_main_page_state()
        messagebox.showinfo("Store", "Record stored successfully.")

    def clear_action(self):
        for var in [self.m_var, self.n_var, self.k_var, self.j_var, self.s_var]:
            var.set("")

        self._sync_at_least_from_s()

        self.mode_var.set("random")
        self.set_values_content("")
        self.results_text.delete("1.0", tk.END)

        for entry in self.manual_entries:
            entry.delete(0, tk.END)

        self.current_result_pages = []
        self.current_page_index = 0
        self.last_solver_result = None
        self.main_page_state = None

    def print_action(self):
        messagebox.showinfo("Print", "Print function will be added later.")

    def display_record(self):
        selection = self.record_listbox.curselection()
        if not selection:
            messagebox.showwarning("Display", "Please select a record first.")
            return

        if load_record_by_name is None:
            messagebox.showerror("Display Error", "Cannot import load_record_by_name from storage.py.")
            return

        index = selection[0]
        record_name = self.record_names[index]
        content = load_record_by_name(record_name)

        self.record_detail_text.delete("1.0", tk.END)
        self.record_detail_text.insert(tk.END, content)

    def delete_record(self):
        selection = self.record_listbox.curselection()
        if not selection:
            messagebox.showwarning("Delete", "Please select a record first.")
            return

        if delete_record_by_name is None:
            messagebox.showerror("Delete Error", "Cannot import delete_record_by_name from storage.py.")
            return

        index = selection[0]
        record_name = self.record_names[index]

        confirmed = messagebox.askyesno("Delete", f"Delete record '{record_name}'?")
        if not confirmed:
            return

        try:
            delete_record_by_name(record_name)
        except Exception as exc:
            messagebox.showerror("Delete Error", f"Failed to delete record:\n{exc}")
            return

        self.refresh_record_listbox()
        self.record_detail_text.delete("1.0", tk.END)
        messagebox.showinfo("Delete", "Record deleted successfully.")