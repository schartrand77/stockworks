"""Tkinter-based GUI client for the StockWorks inventory system."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from datetime import datetime
from typing import Dict, List, Optional

from sqlmodel import select

from .db import init_db, session_scope
from .models import InventoryItem, Material, StockMovement


class StockWorksApp(tk.Tk):
    """Desktop GUI for managing materials, inventory, and pricing."""

    def __init__(self) -> None:
        super().__init__()
        self.title("StockWorks Inventory")
        self.minsize(1100, 680)
        init_db()

        self.material_cache: Dict[int, Material] = {}
        self.inventory_cache: Dict[int, InventoryItem] = {}
        self.material_choice_values: List[str] = []

        self.material_comboboxes: List[ttk.Combobox] = []

        self._build_layout()
        self.refresh_materials()
        self.refresh_inventory()

    # ------------------------------------------------------------------
    # Layout helpers
    def _build_layout(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        notebook = ttk.Notebook(self)
        notebook.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)

        self.material_tab = self._build_material_tab(notebook)
        self.inventory_tab = self._build_inventory_tab(notebook)
        self.pricing_tab = self._build_pricing_tab(notebook)

        notebook.add(self.material_tab, text="Materials")
        notebook.add(self.inventory_tab, text="Inventory")
        notebook.add(self.pricing_tab, text="Pricing")

    def _build_material_tab(self, notebook: ttk.Notebook) -> ttk.Frame:
        tab = ttk.Frame(notebook)
        tab.columnconfigure(0, weight=3)
        tab.columnconfigure(1, weight=2)
        tab.rowconfigure(0, weight=1)

        # Material table
        columns = ("Name", "Filament", "Color", "Price/gram", "Spool (g)", "Supplier", "Brand")
        self.material_tree = ttk.Treeview(tab, columns=columns, show="headings", height=14, selectmode="browse")
        for col in columns:
            anchor = "w"
            width = 120 if col not in {"Price/gram", "Spool (g)"} else 90
            self.material_tree.heading(col, text=col)
            self.material_tree.column(col, width=width, anchor=anchor)
        self.material_tree.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=(0, 10))
        self.material_tree.bind("<<TreeviewSelect>>", self._on_material_select)

        tree_scroll = ttk.Scrollbar(tab, orient="vertical", command=self.material_tree.yview)
        self.material_tree.configure(yscrollcommand=tree_scroll.set)
        tree_scroll.grid(row=0, column=0, sticky="nse", padx=(0, 10), pady=(0, 10))

        # Form
        form_frame = ttk.LabelFrame(tab, text="Edit material")
        form_frame.grid(row=0, column=1, sticky="nsew")
        form_frame.columnconfigure(1, weight=1)

        entry_fields = [
            ("name", "Name"),
            ("filament_type", "Filament type"),
            ("color", "Color"),
            ("supplier", "Supplier"),
            ("brand", "Brand"),
            ("price_per_gram", "Price per gram"),
            ("spool_weight_grams", "Spool weight (g)"),
        ]
        self.material_vars: Dict[str, tk.StringVar] = {}
        for row, (field, label) in enumerate(entry_fields):
            ttk.Label(form_frame, text=label).grid(row=row, column=0, sticky="w", padx=6, pady=4)
            var = tk.StringVar()
            self.material_vars[field] = var
            ttk.Entry(form_frame, textvariable=var).grid(row=row, column=1, sticky="ew", padx=6, pady=4)

        ttk.Label(form_frame, text="Notes").grid(row=len(entry_fields), column=0, sticky="nw", padx=6, pady=6)
        self.material_notes = tk.Text(form_frame, height=4)
        self.material_notes.grid(
            row=len(entry_fields), column=1, sticky="nsew", padx=6, pady=6
        )
        form_frame.rowconfigure(len(entry_fields), weight=1)

        btn_frame = ttk.Frame(form_frame)
        btn_frame.grid(row=len(entry_fields) + 1, column=0, columnspan=2, pady=6)
        ttk.Button(btn_frame, text="Add", command=self.add_material).grid(row=0, column=0, padx=4)
        ttk.Button(btn_frame, text="Update", command=self.update_material).grid(row=0, column=1, padx=4)
        ttk.Button(btn_frame, text="Delete", command=self.delete_material).grid(row=0, column=2, padx=4)
        ttk.Button(btn_frame, text="Clear", command=self.clear_material_form).grid(row=0, column=3, padx=4)

        return tab

    def _build_inventory_tab(self, notebook: ttk.Notebook) -> ttk.Frame:
        tab = ttk.Frame(notebook)
        tab.rowconfigure(0, weight=1)
        tab.columnconfigure(0, weight=3)
        tab.columnconfigure(1, weight=2)

        columns = ("Material", "Location", "Qty (g)", "Reorder", "Spool serial", "Unit cost")
        self.inventory_tree = ttk.Treeview(tab, columns=columns, show="headings", height=12)
        for col in columns:
            anchor = "w"
            width = 140 if col in {"Material", "Location"} else 100
            self.inventory_tree.heading(col, text=col)
            self.inventory_tree.column(col, width=width, anchor=anchor)
        self.inventory_tree.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=(0, 10))
        self.inventory_tree.bind("<<TreeviewSelect>>", self._on_inventory_select)

        inv_scroll = ttk.Scrollbar(tab, orient="vertical", command=self.inventory_tree.yview)
        self.inventory_tree.configure(yscrollcommand=inv_scroll.set)
        inv_scroll.grid(row=0, column=0, sticky="nse", padx=(0, 10), pady=(0, 10))

        # Form for inventory item
        form = ttk.LabelFrame(tab, text="Inventory details")
        form.grid(row=0, column=1, sticky="nsew", pady=(0, 10))
        form.columnconfigure(1, weight=1)

        self.inventory_vars: Dict[str, tk.StringVar] = {
            "material": tk.StringVar(),
            "location": tk.StringVar(),
            "quantity_grams": tk.StringVar(),
            "reorder_level": tk.StringVar(),
            "spool_serial": tk.StringVar(),
            "unit_cost_override": tk.StringVar(),
        }

        ttk.Label(form, text="Material").grid(row=0, column=0, sticky="w", padx=6, pady=4)
        material_combo = ttk.Combobox(form, textvariable=self.inventory_vars["material"], state="readonly")
        material_combo.grid(row=0, column=1, sticky="ew", padx=6, pady=4)
        self.material_comboboxes.append(material_combo)

        labels = [
            ("location", "Location"),
            ("quantity_grams", "Quantity (g)"),
            ("reorder_level", "Reorder level (g)"),
            ("spool_serial", "Spool serial"),
            ("unit_cost_override", "Unit cost override"),
        ]
        for idx, (field, label) in enumerate(labels, start=1):
            ttk.Label(form, text=label).grid(row=idx, column=0, sticky="w", padx=6, pady=4)
            ttk.Entry(form, textvariable=self.inventory_vars[field]).grid(row=idx, column=1, sticky="ew", padx=6, pady=4)

        btn_frame = ttk.Frame(form)
        btn_frame.grid(row=len(labels) + 1, column=0, columnspan=2, pady=6)
        ttk.Button(btn_frame, text="Add", command=self.add_inventory).grid(row=0, column=0, padx=4)
        ttk.Button(btn_frame, text="Update", command=self.update_inventory).grid(row=0, column=1, padx=4)
        ttk.Button(btn_frame, text="Delete", command=self.delete_inventory).grid(row=0, column=2, padx=4)
        ttk.Button(btn_frame, text="Clear", command=self.clear_inventory_form).grid(row=0, column=3, padx=4)

        # Movement history
        movement_frame = ttk.LabelFrame(tab, text="Movement history")
        movement_frame.grid(row=1, column=0, columnspan=2, sticky="nsew")
        movement_frame.columnconfigure(0, weight=1)
        movement_frame.rowconfigure(0, weight=1)

        movement_columns = ("Date", "Type", "Change (g)", "Reference", "Note")
        self.movement_tree = ttk.Treeview(movement_frame, columns=movement_columns, show="headings", height=8)
        for col in movement_columns:
            width = 140 if col == "Note" else 120
            self.movement_tree.heading(col, text=col)
            self.movement_tree.column(col, width=width, anchor="w")
        self.movement_tree.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=(0, 10))

        move_scroll = ttk.Scrollbar(movement_frame, orient="vertical", command=self.movement_tree.yview)
        self.movement_tree.configure(yscrollcommand=move_scroll.set)
        move_scroll.grid(row=0, column=0, sticky="nse", padx=(0, 10), pady=(0, 10))

        log_frame = ttk.Frame(movement_frame)
        log_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        for idx in range(4):
            log_frame.columnconfigure(idx, weight=1)

        ttk.Label(log_frame, text="Movement type").grid(row=0, column=0, sticky="w")
        self.movement_type_var = tk.StringVar(value="incoming")
        ttk.Combobox(
            log_frame,
            values=["incoming", "outgoing", "adjustment"],
            textvariable=self.movement_type_var,
            state="readonly",
        ).grid(row=1, column=0, sticky="ew", padx=4)

        ttk.Label(log_frame, text="Change (grams)").grid(row=0, column=1, sticky="w")
        self.movement_change_var = tk.StringVar()
        ttk.Entry(log_frame, textvariable=self.movement_change_var).grid(row=1, column=1, sticky="ew", padx=4)

        ttk.Label(log_frame, text="Reference").grid(row=0, column=2, sticky="w")
        self.movement_ref_var = tk.StringVar()
        ttk.Entry(log_frame, textvariable=self.movement_ref_var).grid(row=1, column=2, sticky="ew", padx=4)

        ttk.Label(log_frame, text="Note").grid(row=0, column=3, sticky="w")
        self.movement_note_var = tk.StringVar()
        ttk.Entry(log_frame, textvariable=self.movement_note_var).grid(row=1, column=3, sticky="ew", padx=4)

        ttk.Button(log_frame, text="Log movement", command=self.log_movement).grid(row=1, column=4, padx=8, pady=4)

        return tab

    def _build_pricing_tab(self, notebook: ttk.Notebook) -> ttk.Frame:
        tab = ttk.Frame(notebook)
        tab.columnconfigure(1, weight=1)

        fields = [
            ("material", "Material"),
            ("weight_grams", "Weight (g)"),
            ("print_time_hours", "Print time (hours)"),
            ("machine_hour_rate", "Machine hour rate"),
            ("labor_cost", "Labor cost"),
            ("margin_pct", "Margin (%)"),
        ]
        self.pricing_vars: Dict[str, tk.StringVar] = {key: tk.StringVar() for key, _ in fields}

        row = 0
        ttk.Label(tab, text="Generate a quote based on material usage.").grid(row=row, column=0, columnspan=2, sticky="w", pady=(10, 4), padx=10)
        row += 1

        for key, label in fields:
            ttk.Label(tab, text=label).grid(row=row, column=0, sticky="w", padx=10, pady=6)
            if key == "material":
                combo = ttk.Combobox(tab, textvariable=self.pricing_vars[key], state="readonly")
                combo.grid(row=row, column=1, sticky="ew", padx=10, pady=6)
                self.material_comboboxes.append(combo)
            else:
                ttk.Entry(tab, textvariable=self.pricing_vars[key]).grid(row=row, column=1, sticky="ew", padx=10, pady=6)
            row += 1

        ttk.Button(tab, text="Calculate quote", command=self.calculate_quote).grid(row=row, column=0, columnspan=2, pady=10)
        row += 1

        self.pricing_result_var = tk.StringVar(value="Fill out the form and press Calculate.")
        ttk.Label(tab, textvariable=self.pricing_result_var, anchor="w", justify="left").grid(
            row=row, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 10)
        )

        return tab

    # ------------------------------------------------------------------
    # Material actions
    def add_material(self) -> None:
        data = self._material_form_values(require_all=True)
        if not data:
            return
        with session_scope() as session:
            session.add(Material(**data))
        self.refresh_materials()
        self.clear_material_form()
        messagebox.showinfo("Material created", "Material added successfully.")

    def update_material(self) -> None:
        material_id = self._selected_material_id()
        if not material_id:
            messagebox.showwarning("Select material", "Please choose a material to update.")
            return
        data = self._material_form_values(require_all=True)
        if not data:
            return
        with session_scope() as session:
            material = session.get(Material, material_id)
            if not material:
                messagebox.showerror("Not found", "Material could not be located.")
                return
            for key, value in data.items():
                setattr(material, key, value)
            session.add(material)
        self.refresh_materials()
        messagebox.showinfo("Material updated", "Changes saved.")

    def delete_material(self) -> None:
        material_id = self._selected_material_id()
        if not material_id:
            messagebox.showwarning("Select material", "Please choose a material to delete.")
            return
        if not messagebox.askyesno("Delete material", "Delete the selected material and related inventory?"):
            return
        with session_scope() as session:
            material = session.get(Material, material_id)
            if not material:
                messagebox.showerror("Not found", "Material could not be located.")
                return
            # cascade removal will drop inventory via FK constraints
            session.delete(material)
        self.refresh_materials()
        self.refresh_inventory()
        self.clear_material_form()
        messagebox.showinfo("Material deleted", "Material removed.")

    def refresh_materials(self) -> None:
        self.material_tree.delete(*self.material_tree.get_children())
        with session_scope() as session:
            materials = session.exec(select(Material).order_by(Material.name)).all()
        self.material_cache = {m.id: m for m in materials if m.id is not None}
        for material in materials:
            self.material_tree.insert(
                "",
                "end",
                iid=str(material.id),
                values=(
                    material.name,
                    material.filament_type,
                    material.color,
                    f"${material.price_per_gram:.4f}",
                    material.spool_weight_grams,
                    material.supplier or "",
                    material.brand or "",
                ),
            )
        self._update_material_comboboxes(materials)

    def clear_material_form(self) -> None:
        for var in self.material_vars.values():
            var.set("")
        self.material_notes.delete("1.0", "end")
        self.material_tree.selection_remove(self.material_tree.selection())

    def _material_form_values(self, *, require_all: bool) -> Optional[Dict[str, object]]:
        try:
            price = float(self.material_vars["price_per_gram"].get())
            spool = int(self.material_vars["spool_weight_grams"].get())
        except ValueError:
            messagebox.showerror("Invalid input", "Price per gram and spool weight must be numeric.")
            return None

        data = {
            "name": self.material_vars["name"].get().strip(),
            "filament_type": self.material_vars["filament_type"].get().strip(),
            "color": self.material_vars["color"].get().strip(),
            "supplier": self.material_vars["supplier"].get().strip() or None,
            "brand": self.material_vars["brand"].get().strip() or None,
            "price_per_gram": price,
            "spool_weight_grams": spool,
            "notes": self.material_notes.get("1.0", "end").strip() or None,
        }
        if require_all and not all(data[field] for field in ("name", "filament_type", "color")):
            messagebox.showerror("Missing fields", "Name, filament type, and color are required.")
            return None
        return data

    def _selected_material_id(self) -> Optional[int]:
        selection = self.material_tree.selection()
        if not selection:
            return None
        return int(selection[0])

    def _on_material_select(self, _event: object) -> None:
        material_id = self._selected_material_id()
        if not material_id:
            return
        material = self.material_cache.get(material_id)
        if not material:
            return
        self.material_vars["name"].set(material.name)
        self.material_vars["filament_type"].set(material.filament_type)
        self.material_vars["color"].set(material.color)
        self.material_vars["supplier"].set(material.supplier or "")
        self.material_vars["brand"].set(material.brand or "")
        self.material_vars["price_per_gram"].set(str(material.price_per_gram))
        self.material_vars["spool_weight_grams"].set(str(material.spool_weight_grams))
        self.material_notes.delete("1.0", "end")
        self.material_notes.insert("1.0", material.notes or "")

    # ------------------------------------------------------------------
    # Inventory actions
    def add_inventory(self) -> None:
        payload = self._inventory_form_values()
        if not payload:
            return
        with session_scope() as session:
            session.add(InventoryItem(**payload))
        self.refresh_inventory()
        self.clear_inventory_form()
        messagebox.showinfo("Inventory added", "Inventory item created.")

    def update_inventory(self) -> None:
        item_id = self._selected_inventory_id()
        if not item_id:
            messagebox.showwarning("Select item", "Please select an inventory item first.")
            return
        payload = self._inventory_form_values()
        if not payload:
            return
        with session_scope() as session:
            item = session.get(InventoryItem, item_id)
            if not item:
                messagebox.showerror("Not found", "Inventory item no longer exists.")
                return
            for key, value in payload.items():
                setattr(item, key, value)
            session.add(item)
        self.refresh_inventory()
        messagebox.showinfo("Inventory updated", "Inventory item saved.")

    def delete_inventory(self) -> None:
        item_id = self._selected_inventory_id()
        if not item_id:
            messagebox.showwarning("Select item", "Please select an inventory item to delete.")
            return
        if not messagebox.askyesno("Delete inventory", "Delete the selected inventory entry and its movements?"):
            return
        with session_scope() as session:
            item = session.get(InventoryItem, item_id)
            if not item:
                messagebox.showerror("Not found", "Inventory item no longer exists.")
                return
            session.delete(item)
        self.refresh_inventory()
        self.clear_inventory_form()
        self.movement_tree.delete(*self.movement_tree.get_children())
        messagebox.showinfo("Inventory deleted", "Inventory entry removed.")

    def log_movement(self) -> None:
        item_id = self._selected_inventory_id()
        if not item_id:
            messagebox.showwarning("Select item", "Select an inventory item before logging a movement.")
            return
        movement_type = self.movement_type_var.get()
        try:
            change_value = float(self.movement_change_var.get())
        except ValueError:
            messagebox.showerror("Invalid input", "Change amount must be numeric.")
            return
        if movement_type in {"incoming", "outgoing"}:
            if change_value <= 0:
                messagebox.showerror("Invalid amount", "Use a positive number for incoming/outgoing movements.")
                return
            change = change_value if movement_type == "incoming" else -change_value
        else:
            if change_value == 0:
                messagebox.showerror("Invalid amount", "Adjustment change cannot be zero.")
                return
            change = change_value

        with session_scope() as session:
            item = session.get(InventoryItem, item_id)
            if not item:
                messagebox.showerror("Not found", "Inventory item no longer exists.")
                return
            new_qty = item.quantity_grams + change
            if new_qty < 0:
                messagebox.showerror("Invalid movement", "Resulting quantity cannot be negative.")
                return
            movement = StockMovement(
                inventory_item_id=item_id,
                movement_type=movement_type,
                change_grams=change,
                reference=self.movement_ref_var.get().strip() or None,
                note=self.movement_note_var.get().strip() or None,
            )
            item.quantity_grams = new_qty
            session.add(item)
            session.add(movement)

        self.refresh_inventory()
        self._load_movements_for(item_id)
        self.movement_change_var.set("")
        self.movement_note_var.set("")
        self.movement_ref_var.set("")
        messagebox.showinfo("Movement logged", "Stock movement saved.")

    def refresh_inventory(self) -> None:
        self.inventory_tree.delete(*self.inventory_tree.get_children())
        with session_scope() as session:
            statement = select(InventoryItem).order_by(InventoryItem.location)
            items = session.exec(statement).all()
            # eager load material relationship
            for item in items:
                _ = item.material
        self.inventory_cache = {item.id: item for item in items if item.id is not None}
        for item in items:
            material_label = self._format_material_label(item.material)
            self.inventory_tree.insert(
                "",
                "end",
                iid=str(item.id),
                values=(
                    material_label,
                    item.location,
                    f"{item.quantity_grams:.2f}",
                    f"{item.reorder_level:.2f}",
                    item.spool_serial or "",
                    f"${item.unit_cost_override:.4f}" if item.unit_cost_override else "",
                ),
            )

    def clear_inventory_form(self) -> None:
        for var in self.inventory_vars.values():
            var.set("")
        self.inventory_tree.selection_remove(self.inventory_tree.selection())

    def _inventory_form_values(self) -> Optional[Dict[str, object]]:
        material_value = self.inventory_vars["material"].get()
        material_id = self._material_id_from_choice(material_value)
        if not material_id:
            messagebox.showerror("Missing material", "Select a material for the inventory entry.")
            return None
        try:
            quantity = float(self.inventory_vars["quantity_grams"].get() or 0)
            reorder = float(self.inventory_vars["reorder_level"].get() or 0)
            unit_cost = self.inventory_vars["unit_cost_override"].get().strip()
            unit_cost_val = float(unit_cost) if unit_cost else None
        except ValueError:
            messagebox.showerror("Invalid input", "Quantity, reorder level, and unit cost must be numeric.")
            return None
        location = self.inventory_vars["location"].get().strip()
        if not location:
            messagebox.showerror("Missing data", "Location is required.")
            return None
        return {
            "material_id": material_id,
            "location": location,
            "quantity_grams": quantity,
            "reorder_level": reorder,
            "spool_serial": self.inventory_vars["spool_serial"].get().strip() or None,
            "unit_cost_override": unit_cost_val,
        }

    def _selected_inventory_id(self) -> Optional[int]:
        selection = self.inventory_tree.selection()
        if not selection:
            return None
        return int(selection[0])

    def _on_inventory_select(self, _event: object) -> None:
        item_id = self._selected_inventory_id()
        if not item_id:
            return
        item = self.inventory_cache.get(item_id)
        if not item:
            return
        material_choice = self._format_material_choice(item.material)
        if material_choice:
            self.inventory_vars["material"].set(material_choice)
        self.inventory_vars["location"].set(item.location)
        self.inventory_vars["quantity_grams"].set(str(item.quantity_grams))
        self.inventory_vars["reorder_level"].set(str(item.reorder_level))
        self.inventory_vars["spool_serial"].set(item.spool_serial or "")
        self.inventory_vars["unit_cost_override"].set(str(item.unit_cost_override or ""))
        self._load_movements_for(item_id)

    def _load_movements_for(self, item_id: int) -> None:
        self.movement_tree.delete(*self.movement_tree.get_children())
        with session_scope() as session:
            statement = (
                select(StockMovement)
                .where(StockMovement.inventory_item_id == item_id)
                .order_by(StockMovement.created_at.desc())
            )
            movements = session.exec(statement).all()
        for movement in movements:
            timestamp = movement.created_at.strftime("%Y-%m-%d %H:%M")
            self.movement_tree.insert(
                "",
                "end",
                values=(
                    timestamp,
                    movement.movement_type,
                    f"{movement.change_grams:+.2f}",
                    movement.reference or "",
                    movement.note or "",
                ),
            )

    # ------------------------------------------------------------------
    # Pricing actions
    def calculate_quote(self) -> None:
        material_id = self._material_id_from_choice(self.pricing_vars["material"].get())
        if not material_id:
            messagebox.showerror("Missing data", "Select a material to quote against.")
            return
        try:
            weight = float(self.pricing_vars["weight_grams"].get())
            hours = float(self.pricing_vars["print_time_hours"].get())
            machine_rate = float(self.pricing_vars["machine_hour_rate"].get())
            labor = float(self.pricing_vars["labor_cost"].get() or 0)
            margin = float(self.pricing_vars["margin_pct"].get() or 0)
        except ValueError:
            messagebox.showerror("Invalid input", "Weight, print time, machine rate, labor, and margin must be numeric.")
            return
        if weight <= 0 or hours <= 0 or machine_rate <= 0:
            messagebox.showerror("Invalid input", "Weight, print time, and machine rate must be positive.")
            return
        with session_scope() as session:
            material = session.get(Material, material_id)
            if not material:
                messagebox.showerror("Not found", "Material could not be loaded.")
                return
            material_cost = weight * material.price_per_gram
            machine_cost = hours * machine_rate
            subtotal = material_cost + machine_cost + labor
            margin_amount = subtotal * (margin / 100)
            total = subtotal + margin_amount
        result = (
            f"Material ({material.name}): ${material_cost:.2f}\n"
            f"Machine time: ${machine_cost:.2f}\n"
            f"Labor: ${labor:.2f}\n"
            f"Subtotal: ${subtotal:.2f}\n"
            f"Margin: ${margin_amount:.2f}\n"
            f"Total price: ${total:.2f}"
        )
        self.pricing_result_var.set(result)

    # ------------------------------------------------------------------
    # Shared helpers
    def _update_material_comboboxes(self, materials: List[Material]) -> None:
        self.material_choice_values = [self._format_material_choice(material) for material in materials if material.id]
        for combo in self.material_comboboxes:
            combo["values"] = self.material_choice_values
            if combo.get() not in self.material_choice_values:
                combo.set("")

    def _format_material_choice(self, material: Optional[Material]) -> Optional[str]:
        if not material or material.id is None:
            return None
        return f"{material.id} • {material.name} ({material.color})"

    def _format_material_label(self, material: Optional[Material]) -> str:
        if not material:
            return ""
        return f"{material.name} ({material.color})"

    def _material_id_from_choice(self, value: str) -> Optional[int]:
        if not value or "•" not in value:
            return None
        token = value.split("•", 1)[0].strip()
        try:
            return int(token)
        except ValueError:
            return None

    def run(self) -> None:
        self.mainloop()


def main() -> None:
    app = StockWorksApp()
    app.run()


if __name__ == "__main__":
    main()
