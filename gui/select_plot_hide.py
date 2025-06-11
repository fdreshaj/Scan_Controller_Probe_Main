from tkinter import *
from tkinter import ttk

#Returns list of values
def select_plot_hide(n):
    root = Tk()
    root.title("Multi-Select and Alt-Colored Listbox with Instructions")
    selected_values = []
    def make_s_items(n):
        s_params = []
        for i in range(1, n + 1):
            for j in range(1, n + 1):
                s_params.append(f"S{i}{j}")
        return s_params

    def apply_alternate_colors(listbox_widget):
        """Applies alternate background colors to the listbox items."""
        for i in range(listbox_widget.size()):
            if i % 2 == 0:
                listbox_widget.itemconfigure(i, background="#f0f0f0") # Light gray for even rows
            else:
                listbox_widget.itemconfigure(i, background="white") # White for odd rows

    items = make_s_items(n)
    itemsVar = StringVar(value=items)

    # --- Create a Frame to hold the Listbox and the instructions side-by-side ---
    main_frame = ttk.Frame(root, padding="10 10 10 10")
    main_frame.pack(fill=BOTH, expand=True)

    # Create the Listbox with extended selection mode
    l = Listbox(main_frame, listvariable=itemsVar, selectmode=EXTENDED, width=20, height=10) # Set width/height for better initial display

    # Apply alternate colors initially
    apply_alternate_colors(l)

    # Pack the Listbox on the left side of the main_frame
    l.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 10)) # Add right padding

    # --- Create the explanation Label ---
    explanation_text = """
    Click to select traces you want to hide/reshow from the plot.

    Ctrl + Click:
    Add/remove individual items from selection.

    Shift + Click:
    Select a range of items.

    Click & Drag:
    Select multiple contiguous items.
    """
    explanation_label = ttk.Label(main_frame, text=explanation_text, justify=LEFT, wraplength=200) # wraplength to control line breaks
    explanation_label.pack(side=LEFT, fill=Y) # Pack on the right, fill vertically

    
    def show_selected_items():
        selected_indices = l.curselection()
        nonlocal selected_values
        selected_values = [l.get(i) for i in selected_indices]
        print("Selected items:", selected_values)
        if selected_values:
            messagebox.showinfo("Selected Items", "\n".join(selected_values))
            
        else:
            messagebox.showinfo("Selected Items", "No items selected.")
        root.destroy()

    

    from tkinter import messagebox
    select_button = ttk.Button(root, text="Show Selected", command=show_selected_items)
    select_button.pack(pady=10)
    
    root.mainloop()
    return selected_values
    