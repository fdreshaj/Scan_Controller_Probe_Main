## Needed a quick tool for hdf5 reading, gemini one shot

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import h5py
import numpy as np
import os

class HDF5Viewer:
    """
    A Tkinter application to view the contents of an HDF5 file,
    displaying its hierarchical structure (groups, datasets, attributes)
    and detailed information about selected items.
    """
    def __init__(self, master):
        self.master = master
        master.title("HDF5 File Viewer")
        master.geometry("1000x700") # Larger default window size
        master.resizable(True, True)

        self.hdf5_path = tk.StringVar()
        self.status_message = tk.StringVar()

        self._create_widgets()
        self.current_hdf5_file = None # To hold the h5py file object

    def _create_widgets(self):
        """Creates and arranges all GUI widgets."""
        # Styling
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TFrame', background='#e0e0e0')
        style.configure('TLabel', background='#e0e0e0', font=('Inter', 10))
        style.configure('TButton', font=('Inter', 10, 'bold'), padding=10)
        style.configure('TEntry', font=('Inter', 10), padding=5)
        style.configure('Treeview', font=('Inter', 9), rowheight=22)
        style.configure('Treeview.Heading', font=('Inter', 10, 'bold'))

        # Top Frame for file selection
        top_frame = ttk.Frame(self.master, padding="10")
        top_frame.pack(fill=tk.X)

        ttk.Label(top_frame, text="HDF5 File:").pack(side=tk.LEFT, padx=5)
        ttk.Entry(top_frame, textvariable=self.hdf5_path, width=80, state='readonly').pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        ttk.Button(top_frame, text="Browse...", command=self._select_hdf5_file).pack(side=tk.LEFT, padx=5)

        # Main Content Frame (Treeview on left, Details on right)
        content_frame = ttk.Frame(self.master, padding="10")
        content_frame.pack(fill=tk.BOTH, expand=True)

        # Treeview for HDF5 structure
        self.tree = ttk.Treeview(content_frame, selectmode='browse')
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        # Scrollbar for Treeview
        tree_scrollbar = ttk.Scrollbar(content_frame, orient="vertical", command=self.tree.yview)
        tree_scrollbar.pack(side=tk.LEFT, fill=tk.Y)
        self.tree.configure(yscrollcommand=tree_scrollbar.set)

        # Text area for details
        self.details_text = tk.Text(content_frame, wrap=tk.WORD, state='disabled', font=('Inter', 10),
                                    bg='#f8f8f8', fg='#333', padx=10, pady=10)
        self.details_text.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Scrollbar for details text
        details_scrollbar = ttk.Scrollbar(content_frame, orient="vertical", command=self.details_text.yview)
        details_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.details_text.configure(yscrollcommand=details_scrollbar.set)

        # Status Bar
        status_bar = ttk.Label(self.master, textvariable=self.status_message, relief=tk.SUNKEN, anchor=tk.W, font=('Inter', 9))
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # Bind selection event for the treeview
        self.tree.bind('<<TreeviewSelect>>', self._on_tree_select)

    def _select_hdf5_file(self):
        """Opens a file dialog for selecting an HDF5 file."""
        filepath = filedialog.askopenfilename(
            title="Select HDF5 File",
            filetypes=[("HDF5 files", "*.h5 *.hdf5"), ("All files", "*.*")]
        )
        if filepath:
            self.hdf5_path.set(filepath)
            self.status_message.set(f"Selected HDF5: {os.path.basename(filepath)}")
            self._load_hdf5_file(filepath)

    def _load_hdf5_file(self, filepath):
        """
        Loads the selected HDF5 file and populates the Treeview.
        """
        # Close any previously opened file
        if self.current_hdf5_file:
            self.current_hdf5_file.close()
            self.current_hdf5_file = None

        # Clear existing treeview content
        for item in self.tree.get_children():
            self.tree.delete(item)

        self.details_text.config(state='normal')
        self.details_text.delete(1.0, tk.END)
        self.details_text.config(state='disabled')

        try:
            self.current_hdf5_file = h5py.File(filepath, 'r')
            self.status_message.set(f"Loading '{os.path.basename(filepath)}'...")
            self.master.update_idletasks() # Update GUI

            # Add root node for the file
            file_node = self.tree.insert('', 'end', text=os.path.basename(filepath), open=True, tags=('file', filepath))

            self._populate_tree(file_node, self.current_hdf5_file)
            self.status_message.set(f"Successfully loaded '{os.path.basename(filepath)}'.")

        except FileNotFoundError:
            messagebox.showerror("File Error", f"HDF5 file not found: {filepath}")
            self.status_message.set("Failed to load HDF5 file.")
        except Exception as e:
            messagebox.showerror("HDF5 Error", f"An error occurred while opening/reading HDF5 file: {e}")
            self.status_message.set("Failed to load HDF5 file.")

    def _populate_tree(self, parent_node, h5_obj):
        """
        Recursively populates the Treeview with groups, datasets, and attributes.

        Args:
            parent_node (str): The ID of the parent node in the Treeview.
            h5_obj (h5py.Group or h5py.File): The current HDF5 group or file object.
        """
        # Add attributes first if they exist
        if h5_obj.attrs:
            attrs_node = self.tree.insert(parent_node, 'end', text="Attributes", open=False, tags=('attributes',))
            for key, value in h5_obj.attrs.items():
                self.tree.insert(attrs_node, 'end', text=f"{key}: {value}", tags=('attribute_item',))

        # Add child groups and datasets
        for key in h5_obj.keys():
            item = h5_obj[key]
            if isinstance(item, h5py.Group):
                group_node = self.tree.insert(parent_node, 'end', text=key + "/", open=False, tags=('group', item.name))
                self._populate_tree(group_node, item) # Recurse for subgroups
            elif isinstance(item, h5py.Dataset):
                # Store full path for easy access later
                dataset_node = self.tree.insert(parent_node, 'end', text=f"{key} (Dataset)", open=False, tags=('dataset', item.name))
                # Add dataset properties as children
                self.tree.insert(dataset_node, 'end', text=f"Shape: {item.shape}", tags=('dataset_prop',))
                self.tree.insert(dataset_node, 'end', text=f"Dtype: {item.dtype}", tags=('dataset_prop',))
                if item.attrs:
                    ds_attrs_node = self.tree.insert(dataset_node, 'end', text="Attributes", open=False, tags=('attributes',))
                    for attr_key, attr_value in item.attrs.items():
                        self.tree.insert(ds_attrs_node, 'end', text=f"{attr_key}: {attr_value}", tags=('attribute_item',))


    def _on_tree_select(self, event):
        """
        Event handler for Treeview selection. Displays details of the selected item.
        """
        selected_item_id = self.tree.selection()
        if not selected_item_id:
            return

        selected_item_id = selected_item_id[0] # Get the first selected item
        item_tags = self.tree.item(selected_item_id, 'tags')
        item_text = self.tree.item(selected_item_id, 'text')

        self.details_text.config(state='normal')
        self.details_text.delete(1.0, tk.END)

        if 'file' in item_tags and self.current_hdf5_file:
            self.details_text.insert(tk.END, f"HDF5 File: {os.path.basename(self.hdf5_path.get())}\n")
            self.details_text.insert(tk.END, f"Number of top-level groups: {len(self.current_hdf5_file.keys())}\n\n")
            self.details_text.insert(tk.END, "Top-level Groups:\n")
            for key in self.current_hdf5_file.keys():
                self.details_text.insert(tk.END, f"- {key}\n")

        elif 'group' in item_tags and self.current_hdf5_file:
            group_path = item_tags[1] # The full HDF5 path is stored as the second tag
            group = self.current_hdf5_file[group_path]
            self.details_text.insert(tk.END, f"Group: {group.name}\n\n")
            self.details_text.insert(tk.END, "Attributes:\n")
            if group.attrs:
                for key, value in group.attrs.items():
                    self.details_text.insert(tk.END, f"  {key}: {value}\n")
            else:
                self.details_text.insert(tk.END, "  No attributes.\n")

            self.details_text.insert(tk.END, "\nDatasets in Group:\n")
            for key in group.keys():
                if isinstance(group[key], h5py.Dataset):
                    dataset = group[key]
                    self.details_text.insert(tk.END, f"  - {dataset.name.split('/')[-1]} (Shape: {dataset.shape}, Dtype: {dataset.dtype})\n")

        elif 'dataset' in item_tags and self.current_hdf5_file:
            dataset_path = item_tags[1] # The full HDF5 path is stored as the second tag
            dataset = self.current_hdf5_file[dataset_path]
            self.details_text.insert(tk.END, f"Dataset: {dataset.name.split('/')[-1]}\n")
            self.details_text.insert(tk.END, f"Full Path: {dataset.name}\n")
            self.details_text.insert(tk.END, f"Shape: {dataset.shape}\n")
            self.details_text.insert(tk.END, f"Dtype: {dataset.dtype}\n\n")

            self.details_text.insert(tk.END, "Attributes:\n")
            if dataset.attrs:
                for key, value in dataset.attrs.items():
                    self.details_text.insert(tk.END, f"  {key}: {value}\n")
            else:
                self.details_text.insert(tk.END, "  No attributes.\n")

            self.details_text.insert(tk.END, "\nFirst 10 values (or fewer if smaller):\n")
            try:
                # Handle different data types for display
                if dataset.dtype == np.complex64 or dataset.dtype == np.complex128:
                    # For complex data, show real and imag parts
                    values_to_show = dataset[:10]
                    for i, val in enumerate(values_to_show):
                        self.details_text.insert(tk.END, f"  [{i}]: {val.real:.4e} + {val.imag:.4e}j\n")
                else:
                    values_to_show = dataset[:10]
                    for i, val in enumerate(values_to_show):
                        self.details_text.insert(tk.END, f"  [{i}]: {val}\n")
            except Exception as e:
                self.details_text.insert(tk.END, f"  Could not display values: {e}\n")

        elif 'attributes' in item_tags:
            # Parent is a group or dataset, its attributes are displayed
            parent_id = self.tree.parent(selected_item_id)
            parent_tags = self.tree.item(parent_id, 'tags')
            if 'group' in parent_tags and self.current_hdf5_file:
                obj_path = parent_tags[1]
                obj = self.current_hdf5_file[obj_path]
                self.details_text.insert(tk.END, f"Attributes for Group: {obj.name}\n\n")
                for key, value in obj.attrs.items():
                    self.details_text.insert(tk.END, f"  {key}: {value}\n")
            elif 'dataset' in parent_tags and self.current_hdf5_file:
                obj_path = parent_tags[1]
                obj = self.current_hdf5_file[obj_path]
                self.details_text.insert(tk.END, f"Attributes for Dataset: {obj.name.split('/')[-1]}\n\n")
                for key, value in obj.attrs.items():
                    self.details_text.insert(tk.END, f"  {key}: {value}\n")
            else:
                self.details_text.insert(tk.END, "Select a group or dataset to view its attributes.\n")

        elif 'attribute_item' in item_tags or 'dataset_prop' in item_tags:
            self.details_text.insert(tk.END, f"Detail: {item_text}\n")
            self.details_text.insert(tk.END, "Select a group or dataset to view more details.\n")

        else:
            self.details_text.insert(tk.END, "Select an item in the HDF5 tree to view its details here.\n")

        self.details_text.config(state='disabled')

    def _close_hdf5_file(self):
        """Closes the currently opened HDF5 file."""
        if self.current_hdf5_file:
            self.current_hdf5_file.close()
            self.current_hdf5_file = None
            print("HDF5 file closed.")

if __name__ == "__main__":
    root = tk.Tk()
    app = HDF5Viewer(root)
    # Ensure the HDF5 file is closed when the window is closed
    root.protocol("WM_DELETE_WINDOW", lambda: (app._close_hdf5_file(), root.destroy()))
    root.mainloop()