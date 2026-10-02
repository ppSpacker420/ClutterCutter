"""Tkinter GUI.

The GUI is a thin shell over the same scan/plan/apply core the CLI uses, so
the preview it shows and the moves it performs come from identical code.

Safety posture in the UI: the APPLY button is disabled until a scan has
produced a non-empty plan, and applying always shows a confirmation dialog
first.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from . import __version__
from .cli import human
from .mover import apply_plan
from .planner import Plan, build_plan
from .scanner import scan


class ClutterCutterApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"ClutterCutter {__version__}")
        self.geometry("820x560")
        self.minsize(680, 440)

        self.plan: Plan | None = None
        self.root_dir: Path | None = None

        self.folder_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Choose a folder, then press Scan.")
        self.include_protected = tk.BooleanVar(value=False)
        self.recursive = tk.BooleanVar(value=False)

        self._build()
        self._update_buttons()

    # ---------------------------------------------------------------- layout
    def _build(self) -> None:
        pad = {"padx": 10, "pady": 6}

        top = ttk.Frame(self)
        top.pack(fill="x", **pad)

        ttk.Label(top, text="Folder:").pack(side="left")
        self.entry = ttk.Entry(top, textvariable=self.folder_var)
        self.entry.pack(side="left", fill="x", expand=True, padx=6)
        ttk.Button(top, text="Browse...", command=self._browse).pack(side="left")
        self.scan_btn = ttk.Button(top, text="Scan", command=self._scan)
        self.scan_btn.pack(side="left", padx=(6, 0))

        opts = ttk.Frame(self)
        opts.pack(fill="x", **pad)
        ttk.Checkbutton(
            opts, text="Include unclassified files",
            variable=self.include_protected,
        ).pack(side="left")
        ttk.Checkbutton(
            opts, text="Include subfolders", variable=self.recursive
        ).pack(side="left", padx=14)

        # Preview
        mid = ttk.LabelFrame(self, text="Preview (nothing has moved yet)")
        mid.pack(fill="both", expand=True, padx=10, pady=6)

        cols = ("name", "category", "size", "destination")
        self.tree = ttk.Treeview(mid, columns=cols, show="headings")
        self.tree.heading("name", text="File")
        self.tree.heading("category", text="Category")
        self.tree.heading("size", text="Size")
        self.tree.heading("destination", text="Moves to")
        self.tree.column("name", width=210)
        self.tree.column("category", width=110)
        self.tree.column("size", width=90, anchor="e")
        self.tree.column("destination", width=330)
        self.tree.pack(fill="both", expand=True, padx=6, pady=6)

        # Skipped panel
        skip_frame = ttk.LabelFrame(self, text="Left alone")
        skip_frame.pack(fill="both", expand=False, padx=10, pady=6)
        self.skip_tree = ttk.Treeview(skip_frame, columns=("name", "reason"), show="headings")
        self.skip_tree.heading("name", text="File")
        self.skip_tree.heading("reason", text="Reason")
        self.skip_tree.column("name", width=210)
        self.skip_tree.column("reason", width=440)
        self.skip_tree.pack(fill="both", expand=True, padx=6, pady=6)

        # Actions
        bottom = ttk.Frame(self)
        bottom.pack(fill="x", **pad)
        ttk.Label(bottom, textvariable=self.status_var).pack(side="left")
        self.apply_btn = ttk.Button(bottom, text="Apply moves", command=self._apply)
        self.apply_btn.pack(side="right")
        self.reset_btn = ttk.Button(bottom, text="Clear", command=self._clear)
        self.reset_btn.pack(side="right", padx=6)

    # ---------------------------------------------------------------- actions
    def _browse(self) -> None:
        chosen = filedialog.askdirectory(title="Choose a folder to organise")
        if chosen:
            self.folder_var.set(chosen)

    def _clear(self) -> None:
        self.tree.delete(*self.tree.get_children())
        self.skip_tree.delete(*self.skip_tree.get_children())
        self.plan = None
        self.root_dir = None
        self.status_var.set("Choose a folder, then press Scan.")
        self._update_buttons()

    def _scan(self) -> None:
        raw = self.folder_var.get().strip()
        if not raw:
            messagebox.showwarning("No folder", "Pick a folder first.")
            return

        root = Path(raw).expanduser()
        if not root.is_dir():
            messagebox.showerror("Not a folder", f"{root} is not a directory.")
            return

        try:
            report = scan(root, recursive=self.recursive.get())
            plan = build_plan(report, root, include_protected=self.include_protected.get())
        except OSError as exc:
            messagebox.showerror("Scan failed", str(exc))
            return

        self.plan = plan
        self.root_dir = root

        self.tree.delete(*self.tree.get_children())
        for m in plan.moves:
            self.tree.insert("", "end", values=(
                m.src.name, m.category, human(m.size),
                f"{m.dst.parent.name}/{m.dst.name}",
            ))

        self.skip_tree.delete(*self.skip_tree.get_children())
        for s in plan.skips:
            self.skip_tree.insert("", "end", values=(s.path.name, s.reason))
        for name, reason in report.skipped:
            self.skip_tree.insert("", "end", values=(name, f"scan: {reason}"))

        n = len(plan.moves)
        if n:
            self.status_var.set(
                f"{n} file(s) ready to move, {human(plan.total_bytes)}. "
                f"{len(plan.skips)} left alone."
            )
        else:
            self.status_var.set("Nothing to move in this folder.")
        self._update_buttons()

    def _apply(self) -> None:
        if not self.plan or not self.plan.moves or self.root_dir is None:
            return

        n = len(self.plan.moves)
        if not messagebox.askyesno(
            "Confirm",
            f"Move {n} file(s) into category folders inside:\n\n{self.root_dir}\n\n"
            "Nothing is deleted or overwritten. Files that cannot be moved "
            "will be skipped and reported.",
        ):
            self.status_var.set("Cancelled. Nothing was changed.")
            return

        result = apply_plan(self.plan)

        if result.failed:
            self.status_var.set(f"Finished with errors: {result.summary()}")
            detail = "\n".join(f"{f.path.name}: {f.reason}" for f in result.failed[:15])
            messagebox.showwarning(
                "Completed with errors",
                f"{len(result.moved)} moved, {len(result.failed)} could not be moved:\n\n{detail}",
            )
        else:
            self.status_var.set(f"Done: {result.summary()}")
            messagebox.showinfo("Done", f"{len(result.moved)} file(s) moved.")

        # Re-scan so the view reflects reality rather than the stale plan.
        self._scan()

    def _update_buttons(self) -> None:
        ready = bool(self.plan and self.plan.moves)
        self.apply_btn.config(state="normal" if ready else "disabled")


def main() -> None:
    app = ClutterCutterApp()
    app.mainloop()


if __name__ == "__main__":
    main()