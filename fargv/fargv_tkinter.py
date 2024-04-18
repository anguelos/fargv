import tkinter as tk


def is_float_input(P):
    """ Validate whether the input string can be converted to a float. """
    if P == "":
        return True  # Allow clearing the entry
    try:
        float(P)
        return True
    except ValueError:
        return False


def is_int_input(P):
    """ Validate whether the input string can be converted to a float. """
    if P == "":
        return True  # Allow clearing the entry
    try:
        float(P)
        return True
    except ValueError:
        return False


def main():
    root = tk.Tk()
    root.title("Float Entry Example")

    # Setting up a validation command
    validate_float = root.register(is_float_input)

    # Creating an Entry widget that accepts only float-convertible strings
    entry = tk.Entry(root, validate="key", validatecommand=(validate_float, '%P'))
    entry.pack(padx=10, pady=10)

    # Start the GUI event loop
    root.mainloop()

if __name__ == "__main__":
    main()
