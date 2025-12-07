import time
from threading import Thread
import concurrent.futures
from config import *
import random
import tkinter as tk
from tkinter import ttk
from llms import get_clue, get_guesses


def load_words(file_name, num_words):
    """
    Load and randomly select words from a file for the game.

    Args:
        file_name (str): Path to the text file containing words.
        num_words (int): Total number of words to select.

    Returns:
        tuple: (selected_words, target_words, neutral_words, assassin_words)
    """
    try:
        with open(file_name, 'r') as f:
            all_unique_words = list(set(line.strip().upper() for line in f if line.strip()))
    except FileNotFoundError:
        raise Exception("Error", f"File not found: {file_name}. Please create it and add words.")

    if len(all_unique_words) < num_words:
        raise Exception(f"File must contain at least {file_name} unique words. Found {len(all_unique_words)}.")

    selected_words = random.sample(all_unique_words, num_words)
    random.shuffle(selected_words)

    # Assign roles
    target_words = set(selected_words[:8])
    assassin_words = set(selected_words[8:10])
    neutral_words = set(selected_words[10:])

    random.shuffle(selected_words)
    return selected_words, target_words, neutral_words, assassin_words


class CodenamesGUI:
    """GUI class for Cooperative Codenames AI game."""

    def __init__(self, master):
        """
        Initialize GUI, styles, and game state.

        Args:
            master (tk.Tk): Tkinter root window.
        """
        self.master = master
        master.title("Cooperative Codenames AI")

        # Configure styles
        style = ttk.Style()
        style.theme_use("clam")

        style.configure("Word.TButton",
                        font=("Segoe UI", 12, "bold"),
                        padding=8,
                        background="#e6e6e6")
        style.map("Word.TButton", background=[("active", "#d9d9d9")])

        style.configure("Correct.TButton",
                        background="#32a852",
                        foreground="white",
                        font=("Segoe UI", 12, "bold"),
                        padding=8)

        style.configure("Wrong.TButton",
                        background="#bfbfbf",
                        foreground="black",
                        font=("Segoe UI", 12, "bold"),
                        padding=8)

        style.configure("Assassin.TButton",
                        background="black",
                        foreground="white",
                        font=("Segoe UI", 12, "bold"),
                        padding=8)

        # Load words for the game
        self.selected_words, self.target_words, self.neutral_words, self.assassin_words = load_words(
            WORDS_FILE, REQUIRED_WORD_COUNT
        )

        # Game state variables
        self.unguessed_words = self.selected_words
        self.current_target_words = self.target_words.copy()
        self.clues_given = []
        self.total_clues = 0
        self.game_running = True

        # Store button references
        self.buttons = {}
        self.button_vars = {}

        # Dialog text variable
        self.dialog_var = tk.StringVar(value="Clue Giver: …\nGuesser: …")

        # Setup the UI
        self.setup_ui()

        # Start game loop in a separate thread
        Thread(target=self.start_game_loop, daemon=True).start()

    def setup_ui(self):
        """Set up the UI layout including title, buttons grid, and footer."""
        main_frame = ttk.Frame(self.master, padding=20)
        main_frame.pack(fill='both', expand=True)

        # Title
        title_label = ttk.Label(
            main_frame,
            text="✨ Cooperative Codenames — AI Edition ✨",
            font=("Segoe UI", 18, "bold")
        )
        title_label.pack(pady=(0, 10))

        # Dialog label
        dialog_label = ttk.Label(
            main_frame,
            textvariable=self.dialog_var,
            font=("Segoe UI", 13),
            foreground="#333"
        )
        dialog_label.pack(pady=10)

        # Grid for word buttons
        grid_frame = ttk.Frame(main_frame)
        grid_frame.pack(pady=15)

        for i in range(4):
            grid_frame.grid_columnconfigure(i, weight=1)

        # Create 4x4 button grid
        for i in range(4):
            for j in range(4):
                index = i * 4 + j
                word = self.selected_words[index]

                var = tk.StringVar(value=word)
                self.button_vars[word] = var

                btn = ttk.Button(grid_frame, textvariable=var, style="Word.TButton")
                btn.grid(row=i, column=j, padx=7, pady=7, sticky="nsew")
                btn.config(width=16)

                self.buttons[word] = btn

        ttk.Separator(main_frame, orient="horizontal").pack(fill="x", pady=10)

        # Footer
        footer = ttk.Label(
            main_frame,
            text="AI Codenames • by Itsik 😎",
            font=("Segoe UI", 10, "italic"),
            foreground="#777"
        )
        footer.pack()

    def start_game_loop(self):
        """Main game loop handling clue generation and AI guessing."""
        while self.game_running and self.current_target_words:

            # Reset dialog
            self.master.after(0, lambda: self.dialog_var.set(
                "Clue Giver: …\nGuesser:"
            ))

            # AI generates clue
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(
                    get_clue,
                    self.current_target_words,
                    self.neutral_words,
                    self.assassin_words,
                    self.clues_given
                )
                clue, number = future.result(timeout=MAX_THINKING_TIME)

            self.total_clues += 1

            # Display clue
            self.master.after(0, lambda: self.dialog_var.set(
                f"Clue Giver: {clue}, {number}\nGuesser:"
            ))
            time.sleep(0.5)
            self.master.after(0, lambda: self.dialog_var.set(
                f"Clue Giver: {clue}, {number}\nGuesser: Thinking..."
            ))
            time.sleep(TURN_PAUSE_SECONDS)

            # AI guesses words
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(
                    get_guesses, clue, number, self.unguessed_words
                )
                guesses = future.result(timeout=MAX_THINKING_TIME)

            successful_guesses = 0

            for i, guess in enumerate(guesses):
                # Update dialog with guesses
                self.master.after(0, lambda g=i: self.dialog_var.set(
                    f"Clue Giver: {clue}, {number}\nGuesser: {', '.join(guesses[:g + 1])}"
                ))
                time.sleep(1)

                if guess not in self.unguessed_words:
                    continue

                self.unguessed_words.remove(guess)

                # Handle assassin word
                if guess in self.assassin_words:
                    self.game_running = False
                    self.buttons[guess].config(style="Assassin.TButton")
                    break

                # Handle correct guess
                elif guess in self.current_target_words:
                    self.current_target_words.remove(guess)
                    successful_guesses += 1
                    self.buttons[guess].config(style="Correct.TButton")

                    # Check for win
                    if not self.current_target_words:
                        self.game_running = False
                        self.master.after(0, lambda g=i: self.dialog_var.set("Win!"))
                        break

                # Handle wrong guess
                else:
                    self.buttons[guess].config(style="Wrong.TButton")
                    break

                if successful_guesses > number:
                    break


if __name__ == "__main__":
    root = tk.Tk()
    app = CodenamesGUI(root)
    root.mainloop()
