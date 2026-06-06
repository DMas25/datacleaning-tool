import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
from threading import Thread
from coltradata.engine import run_pipeline_from_path

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ColtraDataAi Desktop")
        self.geometry("720x420")
        self.resizable(False, False)
        self.file_path = tk.StringVar()
        self.status = tk.StringVar(value="Select a file to generate a refined Excel report.")
        self.z_thresh = tk.DoubleVar(value=3.0)
        self.include_dashboard = tk.BooleanVar(value=True)
        self._build()

    def _build(self):
        padx = 14
        pady = 10

        ttk.Label(self, text="ColtraDataAi — Desktop Report Generator", font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=padx, pady=(16, 8))

        frame = ttk.Frame(self)
        frame.pack(fill="x", padx=padx, pady=pady)

        ttk.Label(frame, text="Input file:").grid(row=0, column=0, sticky="w")
        entry = ttk.Entry(frame, textvariable=self.file_path, width=72)
        entry.grid(row=1, column=0, padx=(0, 8), pady=(6, 0), sticky="we")
        ttk.Button(frame, text="Browse", command=self.browse).grid(row=1, column=1, pady=(6, 0))

        opts = ttk.LabelFrame(self, text="Options")
        opts.pack(fill="x", padx=padx, pady=pady)

        ttk.Checkbutton(opts, text="Include dashboard visuals", variable=self.include_dashboard).grid(row=0, column=0, sticky="w", padx=10, pady=8)
        ttk.Label(opts, text="Outlier sensitivity (z-score):").grid(row=1, column=0, sticky="w", padx=10)
        ttk.Scale(opts, from_=2.0, to=5.0, variable=self.z_thresh, orient="horizontal", length=240).grid(row=1, column=1, sticky="w", padx=(0, 12))
        ttk.Label(opts, textvariable=tk.StringVar(value="Use 3.0 as standard.")).grid(row=1, column=2, sticky="w")

        ttk.Button(self, text="Generate report", command=self.generate).pack(anchor="w", padx=padx, pady=(14, 4))
        ttk.Label(self, textvariable=self.status, foreground="#1f2937", wraplength=680).pack(anchor="w", padx=padx, pady=(6, 0))

        self.progress = ttk.Progressbar(self, mode="indeterminate", length=660)
        self.progress.pack(anchor="w", padx=padx, pady=(16, 0))

        help_text = (
            "Output workbook includes Raw Data, Cleaned Data, Executive Summary, Data Quality, Key Metrics, "
            "Segmentation, Outlier Log, Data Dictionary, Disclaimer, and Dashboard with visuals."
        )
        ttk.Label(self, text=help_text, wraplength=680, foreground="#4b5563").pack(anchor="w", padx=padx, pady=(12, 0))

    def browse(self):
        path = filedialog.askopenfilename(filetypes=[("Data files", "*.xlsx *.xls *.csv")])
        if path:
            self.file_path.set(path)

    def generate(self):
        path = self.file_path.get().strip()
        if not path:
            messagebox.showwarning("Missing file", "Please select a file first.")
            return
        self.progress.start(10)
        self.status.set("Generating report...")
        Thread(target=self._work, args=(path,), daemon=True).start()

    def _work(self, path):
        try:
            report_path, preview = run_pipeline_from_path(
                path,
                output_dir="output",
                z_threshold=float(self.z_thresh.get()),
                include_dashboard=bool(self.include_dashboard.get()),
            )
            self.after(0, lambda: self._done(report_path, preview))
        except Exception as e:
            self.after(0, lambda: self._error(str(e)))

    def _done(self, report_path, preview):
        self.progress.stop()
        self.status.set(
            f"Report generated successfully: {report_path} | Rows: {preview.get('rows', 0)} | "
            f"Duplicates removed: {preview.get('duplicates_removed', 0)} | Issues: {preview.get('issue_count', 0)}"
        )
        messagebox.showinfo("Success", f"Report saved to:\n{report_path}")

    def _error(self, message):
        self.progress.stop()
        self.status.set("Generation failed.")
        messagebox.showerror("Error", message)

if __name__ == "__main__":
    App().mainloop()
