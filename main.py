import random
import tkinter as tk
import matplotlib.pyplot as plt
from PIL import ImageTk, Image
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from recognize_speech import SpeechRecognizer
from questions import questions

try:
    import vlc
except ImportError:
    vlc = None
import sys

try:
    import pygame

    pygame.mixer.init()
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False


class MillionaireGame:
    def __init__(self, root):
        self.root = root
        self.root.title("Who Wants to Be a Millionaire?")
        self.root.geometry("1280x720")
        self.root.resizable(False, False)

        self.current_question = 0
        self.lifelines = {'50:50': True, 'Phone': True, 'Ask': True}
        self.prize_levels = [100, 200, 300, 500, 1000, 2000, 4000, 8000, 16000, 32000, 64000, 125000, 250000, 500000,
                             1000000]
        self.safe_havens = [4, 9, 14]

        # Initialize audio system variables
        self.current_bg_music = None
        self.bg_music_index = 0
        self.bg_music_playing = False
        self.sound_muted = False  # New flag to track sound muting state
        self.bg_music_files = ['sounds/main_theme_2.mp3', 'sounds/main_theme_3.mp3']

        self.colors = {
            'background': '#020230',  # Dark blue
            'text': '#FFFFFF',  # White
            'highlight': '#FFC000',  # Gold
            'question_bg': '#000040',  # Dark blue
            'button_normal': '#0D0D80',  # Blue
            'button_hover': '#1A1AA0',  # Light blue
            'button_selected': '#FFBA00',  # Gold
            'button_correct': '#00C000',  # Green
            'button_wrong': '#C00000',  # Red
        }

        try:
            self.background_img = ImageTk.PhotoImage(Image.open("images/center.png").resize((1280, 720)))
        except:
            self.background_img = None

        try:
            self.fifty_fifty_icon = ImageTk.PhotoImage(Image.open("images/fifty_fifty.png").resize((50, 50)))
            self.phone_icon = ImageTk.PhotoImage(Image.open("images/phone.png").resize((50, 50)))
            self.ask_icon = ImageTk.PhotoImage(Image.open("images/ask.png").resize((50, 50)))
        except:
            self.fifty_fifty_icon = None
            self.phone_icon = None
            self.ask_icon = None

        # Initialize speech recognizer
        self.speech_recognizer = SpeechRecognizer(self, self.handle_speech)

        # Add microphone icon
        try:
            self.mic_icon = ImageTk.PhotoImage(Image.open("images/microphone.png").resize((50, 50)))
            self.mic_active_icon = ImageTk.PhotoImage(Image.open("images/microphone_active.png").resize((50, 50)))
        except:
            self.mic_icon = None
            self.mic_active_icon = None

        # Audio
        self.sounds = {
            'intro': 'sounds/main_theme_1.mp3',
            'correct': 'sounds/correct_answer.mp3',
            'wrong': 'sounds/wrong_answer.mp3',
        }

        if PYGAME_AVAILABLE:
            pygame.mixer.init()
            # Set up channels for different sounds
            pygame.mixer.set_num_channels(8)
            self.bg_channel = pygame.mixer.Channel(7)  # Reserve channel 7 for background music
            self.fx_channel = pygame.mixer.Channel(6)  # Reserve channel 6 for sound effects

        self.setup_gui()
        self.load_questions_from_file()
        self.start_game()

    def setup_gui(self):
        # Main background
        self.main_frame = tk.Frame(self.root, bg=self.colors['background'], width=1280, height=720)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        if self.background_img:
            bg_label = tk.Label(self.main_frame, image=self.background_img)
            bg_label.place(x=0, y=0, relwidth=1, relheight=1)
        else:
            self.main_frame.configure(bg=self.colors['background'])

        title_label = tk.Label(self.main_frame, text="WHO WANTS TO BE A MILLIONAIRE?",
                               font=("Impact", 30), bg=self.colors['background'], fg=self.colors['highlight'])  # title
        title_label.pack(pady=(20, 10))

        self.game_area = tk.Frame(self.main_frame, bg=self.colors['background'])
        self.game_area.place(relx=0.5, rely=0.45, anchor=tk.CENTER, width=800, height=400)

        self.question_frame = tk.Frame(self.game_area, bg=self.colors['question_bg'],
                                       highlightbackground=self.colors['highlight'],
                                       highlightthickness=2, padx=20, pady=10)
        self.question_frame.pack(pady=(0, 30), fill=tk.X)

        self.question_label = tk.Label(self.question_frame, text="", wraplength=700,
                                       font=("Arial", 16, "bold"), bg=self.colors['question_bg'],
                                       fg=self.colors['text'])
        self.question_label.pack(pady=15)

        # options
        self.option_buttons = []
        self.option_vars = []
        letters = ['A', 'B', 'C', 'D']

        for i in range(4):
            btn_frame = tk.Frame(self.game_area, bg=self.colors['background'])
            btn_frame.pack(pady=5, fill=tk.X)

            var = tk.StringVar(value="")
            self.option_vars.append(var)

            btn = tk.Button(btn_frame, text="", font=("Arial", 14, "bold"),
                            bg=self.colors['button_normal'], fg=self.colors['text'],
                            activebackground=self.colors['button_hover'],
                            bd=2, relief="raised", padx=20, pady=5,
                            command=lambda i=i: self.select_answer(i))

            letter_label = tk.Label(btn_frame, text=f"{letters[i]}:", font=("Arial", 14, "bold"),
                                    bg=self.colors['button_normal'], fg=self.colors['highlight'],
                                    width=3)
            letter_label.pack(side=tk.LEFT, padx=(0, 0))

            btn.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self.option_buttons.append((btn, letter_label))

            btn.bind("<Enter>", lambda event, b=btn: b.config(bg=self.colors['button_hover']))
            btn.bind("<Leave>", lambda event, b=btn, v=var:
            b.config(bg=self.colors['button_selected'] if v.get() == "selected"
            else self.colors['button_normal']))

        self.confirm_button = tk.Button(self.game_area, text="Final Answer", font=("Arial", 14, "bold"),
                                        bg=self.colors['highlight'], fg='black',
                                        state=tk.DISABLED, command=self.confirm_answer)
        self.confirm_button.pack(pady=10)

        self.lifeline_frame = tk.Frame(self.main_frame, bg=self.colors['background'])
        self.lifeline_frame.place(x=20, y=20, width=200, height=150)

        lifeline_title = tk.Label(self.lifeline_frame, text="LIFELINES",
                                  font=("Arial", 14, "bold"), bg=self.colors['background'], fg=self.colors['highlight'])
        lifeline_title.pack(pady=(0, 10))

        lifeline_buttons_frame = tk.Frame(self.lifeline_frame, bg=self.colors['background'])
        lifeline_buttons_frame.pack()

        if self.fifty_fifty_icon:
            self.fifty_fifty_btn = tk.Button(lifeline_buttons_frame, image=self.fifty_fifty_icon,
                                             bg=self.colors['background'], bd=0, command=self.use_fifty_fifty)
        else:
            self.fifty_fifty_btn = tk.Button(lifeline_buttons_frame, text="50:50",
                                             font=("Arial", 12, "bold"),
                                             bg=self.colors['button_normal'], fg=self.colors['text'],
                                             command=self.use_fifty_fifty)
        self.fifty_fifty_btn.grid(row=0, column=0, padx=5)

        if self.phone_icon:
            self.phone_btn = tk.Button(lifeline_buttons_frame, image=self.phone_icon,
                                       bg=self.colors['background'], bd=0, command=self.use_phone)
        else:
            self.phone_btn = tk.Button(lifeline_buttons_frame, text="Phone",
                                       font=("Arial", 12, "bold"),
                                       bg=self.colors['button_normal'], fg=self.colors['text'],
                                       command=self.use_phone)
        self.phone_btn.grid(row=0, column=1, padx=5)

        if self.ask_icon:
            self.ask_btn = tk.Button(lifeline_buttons_frame, image=self.ask_icon,
                                     bg=self.colors['background'], bd=0, command=self.use_ask)
        else:
            self.ask_btn = tk.Button(lifeline_buttons_frame, text="Ask",
                                     font=("Arial", 12, "bold"),
                                     bg=self.colors['button_normal'], fg=self.colors['text'],
                                     command=self.use_ask)
        self.ask_btn.grid(row=0, column=2, padx=5)

        self.speech_frame = tk.Frame(self.main_frame,
                                     bg=self.colors['background'])
        self.speech_frame.place(x=20, y=220, width=200, height=150)

        speech_label = tk.Label(self.speech_frame, text="VOICE ANSWER",
                                font=("Arial", 12, "bold"),
                                bg=self.colors['background'], fg=self.colors['highlight'])
        speech_label.pack(pady=(5, 5))

        if self.mic_icon:
            self.mic_btn = tk.Button(self.speech_frame, image=self.mic_icon,
                                     bg=self.colors['background'], bd=0,
                                     command=self.toggle_speech_recognition)
        else:
            self.mic_btn = tk.Button(self.speech_frame, text="🎤",
                                     font=("Arial", 20, "bold"),
                                     bg=self.colors['button_normal'], fg=self.colors['text'],
                                     command=self.toggle_speech_recognition)
        self.mic_btn.pack(pady=5)

        self.mic_status_label = tk.Label(self.speech_frame, text="Click to speak",
                                         font=("Arial", 10),
                                         bg=self.colors['background'], fg=self.colors['text'])
        self.mic_status_label.pack(pady=2)

        # Add sound control button
        self.sound_frame = tk.Frame(self.main_frame, bg=self.colors['background'])
        self.sound_frame.place(x=20, y=380, width=200, height=80)

        sound_label = tk.Label(self.sound_frame, text="SOUND",
                               font=("Arial", 12, "bold"),
                               bg=self.colors['background'], fg=self.colors['highlight'])
        sound_label.pack(pady=(5, 5))

        self.sound_btn = tk.Button(self.sound_frame, text="🔊",
                                   font=("Arial", 16, "bold"),
                                   bg=self.colors['button_normal'], fg=self.colors['text'],
                                   command=self.toggle_sound)
        self.sound_btn.pack(pady=5)

        self.prize_frame = tk.Frame(self.main_frame, bg=self.colors['background'])
        self.prize_frame.place(x=1050, y=100, width=200, height=500)

        prize_title = tk.Label(self.prize_frame, text="PRIZE LADDER",
                               font=("Arial", 14, "bold"), bg=self.colors['background'], fg=self.colors['highlight'])
        prize_title.pack(pady=(0, 10))

        self.prize_labels = []
        for i in range(len(self.prize_levels) - 1, -1, -1):
            level_frame = tk.Frame(self.prize_frame, bg=self.colors['background'])
            level_frame.pack(fill=tk.X, pady=2)

            formatted_prize = "${:,}".format(self.prize_levels[i])

            q_label = tk.Label(level_frame, text=f"{i + 1}.", width=3,
                               font=("Arial", 12, "bold"),
                               bg=self.colors['background'], fg=self.colors['text'])
            q_label.pack(side=tk.LEFT, padx=(5, 0))

            prize_label = tk.Label(level_frame, text=formatted_prize,
                                   font=("Arial", 12, "bold"),
                                   bg=self.colors['background'], fg=self.colors['text'])
            prize_label.pack(side=tk.RIGHT, padx=(0, 5))

            self.prize_labels.append((q_label, prize_label, level_frame))

        self.current_prize_frame = tk.Frame(self.main_frame, bg=self.colors['background'])
        self.current_prize_frame.place(relx=0.5, rely=0.9, anchor=tk.CENTER)

        self.current_prize_label = tk.Label(self.current_prize_frame,
                                            text="Current Prize: $0",
                                            font=("Arial", 16, "bold"),
                                            bg=self.colors['background'], fg=self.colors['highlight'])
        self.current_prize_label.pack()

        quit_btn = tk.Button(self.main_frame, text="Quit Game",
                             font=("Arial", 12),
                             bg='#880000', fg='white',
                             command=self.quit_game)
        quit_btn.place(x=20, y=680)

        self.setup_timer()

    def load_questions_from_file(self):
        self.questions = []
        level1_questions = random.sample(questions[1], 5)
        level2_questions = random.sample(questions[2], 5)
        level3_questions = random.sample(questions[3], 5)

        self.questions = level1_questions + level2_questions + level3_questions

        print(f"Successfully loaded {len(self.questions)} questions from file")

    def start_game(self):
        self.update_prize_display()
        self.show_question()
        if not self.sound_muted:
            self.play_sound('intro', volume=0.5)

        self.root.after(17000, self.start_background_music)

    def start_background_music(self):
        if PYGAME_AVAILABLE and not self.sound_muted:
            try:
                self.play_background_music()
            except Exception as e:
                print(f"Error starting background music: {e}")

    def play_background_music(self):
        if not PYGAME_AVAILABLE:
            return

        try:
            if self.bg_music_playing:
                self.bg_channel.stop()

            if self.sound_muted:
                self.bg_music_playing = False
                return

            bg_music = pygame.mixer.Sound(self.bg_music_files[self.bg_music_index])

            bg_music.set_volume(0.3)

            self.bg_channel.play(bg_music)

            self.bg_music_playing = True

            self.sound_btn.config(text="🔊")

            duration = int(bg_music.get_length() * 1000)

            self.bg_music_index = (self.bg_music_index + 1) % len(self.bg_music_files)
            self.root.after(duration, self.play_background_music)

        except Exception as e:
            print(f"Error in background music: {e}")
            self.bg_music_playing = False

    def toggle_sound(self):
        if not PYGAME_AVAILABLE:
            return

        if self.sound_muted:
            # Unmute all sounds
            self.sound_muted = False
            self.sound_btn.config(text="🔊")

            # Start background music if it was playing before
            if not self.bg_channel.get_busy():
                self.play_background_music()
        else:
            # Mute all sounds
            self.sound_muted = True
            self.sound_btn.config(text="🔇")

            # Stop all sound channels
            if self.bg_channel.get_busy():
                self.bg_channel.stop()
            if self.fx_channel.get_busy():
                self.fx_channel.stop()

            self.bg_music_playing = False

    def show_question(self):
        for i, (btn, letter_label) in enumerate(self.option_buttons):
            btn.config(bg=self.colors['button_normal'], state=tk.NORMAL)
            letter_label.config(bg=self.colors['button_normal'])
            self.option_vars[i].set("")

        self.confirm_button.config(state=tk.DISABLED)

        question_data = self.questions[self.current_question]
        self.question_label.config(text=question_data["question"])

        for i, option in enumerate(question_data["options"]):
            self.option_buttons[i][0].config(text=option)

        self.update_prize_display()

        # Set up and start the timer based on question number
        if self.current_question < 5:
            # First 5 questions: 60 seconds
            self.start_timer(60)
        elif self.current_question < 10:
            # Questions 6-10: 90 seconds
            self.start_timer(90)
        else:
            # Last 5 questions: no timer
            self.stop_timer()
            self.hide_timer()

    def select_answer(self, selected):
        for i, (btn, letter_label) in enumerate(self.option_buttons):
            if i == selected:
                btn.config(bg=self.colors['button_selected'])
                letter_label.config(bg=self.colors['button_selected'])
                self.option_vars[i].set("selected")
            else:
                btn.config(bg=self.colors['button_normal'])
                letter_label.config(bg=self.colors['button_normal'])
                self.option_vars[i].set("")

        self.confirm_button.config(state=tk.NORMAL)

        self.selected_answer = selected

    def confirm_answer(self):
        for btn, _ in self.option_buttons:
            btn.config(state=tk.DISABLED)
        self.confirm_button.config(state=tk.DISABLED)

        self.root.after(1000, lambda: self.check_answer(self.selected_answer))

    def check_answer(self, selected):
        self.stop_timer()

        correct = self.questions[self.current_question]["correct"]

        self.option_buttons[correct][0].config(bg=self.colors['button_correct'])
        self.option_buttons[correct][1].config(bg=self.colors['button_correct'])

        if selected == correct:
            # Play correct sound
            self.play_sound('correct')
            self.root.after(1500, self.handle_correct_answer)
        else:
            self.option_buttons[selected][0].config(bg=self.colors['button_wrong'])
            self.option_buttons[selected][1].config(bg=self.colors['button_wrong'])
            # Play wrong sound
            self.play_sound('wrong')
            self.root.after(1500, self.game_over)

    def handle_correct_answer(self):
        current_prize = self.prize_levels[self.current_question]
        self.current_prize_label.config(text=f"Current Prize: ${current_prize:,}")

        self.current_question += 1
        if self.current_question >= len(self.questions):
            self.you_win()
        else:
            self.show_question()

    def update_prize_display(self):
        for i, (q_label, prize_label, frame) in enumerate(self.prize_labels):
            level = len(self.prize_levels) - i - 1

            if level == self.current_question:
                frame.config(bg=self.colors['highlight'])
                q_label.config(bg=self.colors['highlight'], fg='black')
                prize_label.config(bg=self.colors['highlight'], fg='black')
            elif level in self.safe_havens and level < self.current_question:
                frame.config(bg='green')
                q_label.config(bg='green', fg='white')
                prize_label.config(bg='green', fg='white')
            elif level < self.current_question:
                frame.config(bg='#404040')
                q_label.config(bg='#404040', fg='white')
                prize_label.config(bg='#404040', fg='white')
            else:
                frame.config(bg=self.colors['background'])
                q_label.config(bg=self.colors['background'], fg=self.colors['text'])
                prize_label.config(bg=self.colors['background'], fg=self.colors['text'])

    def use_fifty_fifty(self):
        if self.lifelines['50:50']:
            # Pause timer while using lifeline
            timer_was_running = self.timer_running
            if timer_was_running:
                self.stop_timer()

            question_data = self.questions[self.current_question]
            correct_index = question_data["correct"]

            incorrect_indices = [i for i in range(4) if i != correct_index]
            disable_indices = random.sample(incorrect_indices, 2)

            for i in disable_indices:
                self.option_buttons[i][0].config(state=tk.DISABLED, text="")
                self.option_buttons[i][1].config(state=tk.DISABLED)

            self.lifelines['50:50'] = False
            self.fifty_fifty_btn.config(state=tk.DISABLED, bg='gray')

            # Restart timer if it was running
            if timer_was_running and self.current_question < 10:
                self.start_timer(self.timer_count)

    def use_phone(self):
        if self.lifelines['Phone']:
            if self.lifelines['50:50']:
                # Pause timer while using lifeline
                timer_was_running = self.timer_running
                if timer_was_running:
                    self.stop_timer()

            phone_window = tk.Toplevel(self.root)
            phone_window.title("Phone a Friend")
            phone_window.geometry("400x300")
            phone_window.configure(bg=self.colors['background'])

            phone_window.geometry(f"+{self.root.winfo_x() + 400}+{self.root.winfo_y() + 200}")

            phone_window.grab_set()

            timer_label = tk.Label(phone_window, text="30", font=("Arial", 24, "bold"),
                                   fg=self.colors['highlight'], bg=self.colors['background'])
            timer_label.pack(pady=10)

            try:
                friend_img = ImageTk.PhotoImage(Image.open("images/friend.png").resize((100, 100)))
                friend_label = tk.Label(phone_window, image=friend_img, bg=self.colors['background'])
                friend_label.image = friend_img  # Keep a reference
                friend_label.pack(pady=10)
            except:
                friend_label = tk.Label(phone_window, text="👤", font=("Arial", 40),
                                        fg=self.colors['text'], bg=self.colors['background'])
                friend_label.pack(pady=10)

            question_data = self.questions[self.current_question]
            correct_index = question_data["correct"]
            options = question_data["options"]

            if random.random() < 0.8:
                guess = options[correct_index]
                confidence = random.randint(70, 95)
            else:
                wrong_options = [option for i, option in enumerate(options) if i != correct_index]
                guess = random.choice(wrong_options)
                confidence = random.randint(60, 85)

            message_text = f"I'm {confidence}% sure the answer is:\n\n{guess}"
            message_var = tk.StringVar()
            message_var.set("Calling your friend...")

            message_label = tk.Label(phone_window, textvariable=message_var,
                                     font=("Arial", 14), bg=self.colors['background'],
                                     fg=self.colors['text'], wraplength=350)
            message_label.pack(pady=10, expand=True)

            close_btn = tk.Button(phone_window, text="Close", font=("Arial", 12),
                                  command=phone_window.destroy, state=tk.DISABLED)
            close_btn.pack(pady=10)

            def countdown(count):
                if count > 0:
                    timer_label.config(text=str(count))
                    phone_window.after(1000, countdown, count - 1)
                else:
                    timer_label.config(text="Time's up!")
                    message_var.set(message_text)
                    close_btn.config(state=tk.NORMAL)

            countdown(5)

            self.lifelines['Phone'] = False
            self.phone_btn.config(state=tk.DISABLED, bg='gray')

            # Restart timer if it was running
            if timer_was_running and self.current_question < 10:
                self.start_timer(self.timer_count)

    def use_ask(self):
        if self.lifelines['Ask']:
            if self.lifelines['50:50']:
                # Pause timer while using lifeline
                timer_was_running = self.timer_running
                if timer_was_running:
                    self.stop_timer()

            ask_window = tk.Toplevel(self.root)
            ask_window.title("Ask the Audience")
            ask_window.geometry("500x400")
            ask_window.configure(bg=self.colors['background'])

            ask_window.geometry(f"+{self.root.winfo_x() + 400}+{self.root.winfo_y() + 150}")

            ask_window.grab_set()

            question_data = self.questions[self.current_question]
            correct_index = question_data["correct"]

            correct_percentage = random.randint(40, 75)
            others_raw = [random.random() for _ in range(3)]
            sum_raw = sum(others_raw)
            others = [round(x / sum_raw * (100 - correct_percentage)) for x in others_raw]

            difference = (100 - correct_percentage) - sum(others)
            others[0] += difference

            percentages = [0] * 4
            other_iter = iter(others)
            for i in range(4):
                if i == correct_index:
                    percentages[i] = correct_percentage
                else:
                    percentages[i] = next(other_iter)

            fig, ax = plt.subplots(figsize=(5, 3))
            fig.patch.set_facecolor(self.colors['background'])
            ax.set_facecolor(self.colors['background'])

            letters = ['A', 'B', 'C', 'D']
            bars = ax.bar(letters, percentages, color=['#4472C4', '#ED7D31', '#A5A5A5', '#FFC000'])

            for bar, percentage in zip(bars, percentages):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width() / 2., height + 1,
                        f'{percentage}%', ha='center', va='bottom',
                        color=self.colors['text'], fontsize=10)

            ax.set_ylim(0, 100)
            ax.set_title('Audience Poll Results', color=self.colors['highlight'], fontsize=14)
            ax.set_xlabel('Answer Options', color=self.colors['text'], fontsize=12)
            ax.set_ylabel('Percentage (%)', color=self.colors['text'], fontsize=12)
            ax.tick_params(axis='x', colors=self.colors['text'])
            ax.tick_params(axis='y', colors=self.colors['text'])
            ax.spines['bottom'].set_color(self.colors['text'])
            ax.spines['left'].set_color(self.colors['text'])
            ax.spines['top'].set_color(self.colors['text'])
            ax.spines['right'].set_color(self.colors['text'])

            canvas = FigureCanvasTkAgg(fig, master=ask_window)
            canvas.draw()
            canvas.get_tk_widget().pack(pady=20, padx=20, fill=tk.BOTH, expand=True)

            title_label = tk.Label(ask_window, text="Audience Poll Results",
                                   font=("Arial", 16, "bold"),
                                   bg=self.colors['background'], fg=self.colors['highlight'])
            title_label.pack(pady=(10, 0))

            options_frame = tk.Frame(ask_window, bg=self.colors['background'])
            options_frame.pack(pady=10, padx=20, fill=tk.X)

            for i, option in enumerate(question_data["options"]):
                option_text = f"{letters[i]}: {option}"
                option_label = tk.Label(options_frame, text=option_text,
                                        font=("Arial", 12),
                                        bg=self.colors['background'], fg=self.colors['text'],
                                        anchor=tk.W)
                option_label.pack(fill=tk.X, pady=2)

            close_btn = tk.Button(ask_window, text="Close", font=("Arial", 12),
                                  command=ask_window.destroy)
            close_btn.pack(pady=10)

            self.lifelines['Ask'] = False
            self.ask_btn.config(state=tk.DISABLED, bg='gray')

            # Restart timer if it was running
            if timer_was_running and self.current_question < 10:
                self.start_timer(self.timer_count)

    def toggle_speech_recognition(self):
        is_listening = self.speech_recognizer.toggle_listening()

        if is_listening:
            self.mic_status_label.config(text="Listening...", fg="green")
            if self.mic_active_icon:
                self.mic_btn.config(image=self.mic_active_icon)
            else:
                self.mic_btn.config(text="🎤", bg="green")
        else:
            self.mic_status_label.config(text="Click to speak", fg=self.colors['text'])
            if self.mic_icon:
                self.mic_btn.config(image=self.mic_icon)
            else:
                self.mic_btn.config(text="🎤", bg=self.colors['button_normal'])

    def handle_speech(self, text):
        if not text:
            return

        text = text.lower().strip()
        question_data = self.questions[self.current_question]
        options = [opt.lower() for opt in question_data["options"]]

        # Find the closest match
        match_index = None
        for i, option in enumerate(options):
            # First check for exact match
            if text == option.lower():
                match_index = i
                break
            # Then check if the option contains the spoken text
            elif text in option.lower():
                match_index = i
                break
            # Finally check if spoken text contains the option
            elif option.lower() in text:
                match_index = i
                break

        if match_index is not None:
            # Highlight the selected answer
            self.select_answer(match_index)

            # If the user said the correct answer
            if match_index == question_data["correct"]:
                self.mic_status_label.config(text="Recognized", fg="white")
                self.speech_recognizer.stop()
                self.toggle_speech_recognition()
                self.root.after(1000, self.confirm_answer)
            else:
                self.mic_status_label.config(text="Recognized", fg="white")
                self.speech_recognizer.stop()
                self.toggle_speech_recognition()
                self.root.after(1000, self.confirm_answer)
        else:
            self.mic_status_label.config(text="Please try again", fg="orange")

    def game_over(self):
        # Reduce background music volume during game over screen if not muted
        if PYGAME_AVAILABLE and self.bg_music_playing and not self.sound_muted:
            self.bg_channel.set_volume(0.1)

        prize = 0
        for safe_level in sorted(self.safe_havens):
            if self.current_question > safe_level:
                prize = self.prize_levels[safe_level]
            else:
                break

        game_over_window = tk.Toplevel(self.root)
        game_over_window.title("Game Over")
        game_over_window.geometry("500x400")
        game_over_window.configure(bg=self.colors['background'])

        game_over_window.geometry(f"+{self.root.winfo_x() + 400}+{self.root.winfo_y() + 150}")

        game_over_window.grab_set()

        try:
            sad_img = ImageTk.PhotoImage(Image.open("images/sad.png").resize((100, 100)))
            sad_label = tk.Label(game_over_window, image=sad_img, bg=self.colors['background'])
            sad_label.image = sad_img  # Keep a reference
            sad_label.pack(pady=20)
        except:
            sad_label = tk.Label(game_over_window, text="😢", font=("Arial", 60),
                                 fg=self.colors['text'], bg=self.colors['background'])
            sad_label.pack(pady=20)

        message_label = tk.Label(game_over_window,
                                 text=f"Sorry, that's the wrong answer!",
                                 font=("Arial", 18, "bold"),
                                 bg=self.colors['background'], fg=self.colors['text'])
        message_label.pack(pady=10)

        prize_label = tk.Label(game_over_window,
                               text=f"You won ${prize:,}",
                               font=("Arial", 24, "bold"),
                               bg=self.colors['background'], fg=self.colors['highlight'])
        prize_label.pack(pady=20)

        buttons_frame = tk.Frame(game_over_window, bg=self.colors['background'])
        buttons_frame.pack(pady=20)

        play_again_btn = tk.Button(buttons_frame, text="Play Again",
                                   font=("Arial", 14),
                                   bg=self.colors['button_normal'], fg=self.colors['text'],
                                   command=lambda: [game_over_window.destroy(), self.restart_game()])
        play_again_btn.grid(row=0, column=0, padx=10)

        quit_btn = tk.Button(buttons_frame, text="Quit",
                             font=("Arial", 14),
                             bg='#880000', fg='white',
                             command=lambda: [game_over_window.destroy(), self.quit_game()])
        quit_btn.grid(row=0, column=1, padx=10)

        # Restore background music volume when window is closed if not muted
        game_over_window.protocol("WM_DELETE_WINDOW",
                                  lambda: [self.restore_bg_music_volume(), game_over_window.destroy()])

    def restore_bg_music_volume(self):
        if PYGAME_AVAILABLE and self.bg_music_playing and not self.sound_muted:
            self.bg_channel.set_volume(0.3)

    def you_win(self):
        if PYGAME_AVAILABLE and self.bg_music_playing and not self.sound_muted:
            self.bg_channel.set_volume(0.1)

        win_window = tk.Toplevel(self.root)
        win_window.title("Congratulations!")
        win_window.geometry("800x600")
        win_window.configure(bg=self.colors['background'])

        # Center the window
        win_window.geometry(f"+{self.root.winfo_x() + 240}+{self.root.winfo_y() + 60}")

        win_window.grab_set()
        video_played = False

        # play video if VLC is available and sound is not muted
        if vlc and not self.sound_muted:
            try:
                # Create VLC instance
                self.vlc_instance = vlc.Instance()
                self.media_player = self.vlc_instance.media_player_new()

                # Create video frame
                video_frame = tk.Frame(win_window, bg='black')
                video_frame.pack(pady=20, expand=True, fill=tk.BOTH)

                # Get window ID and set output window
                win_id = video_frame.winfo_id()
                if sys.platform.startswith('win'):
                    self.media_player.set_hwnd(win_id)
                else:
                    self.media_player.set_xwindow(win_id)

                # Load and play media
                media = self.vlc_instance.media_new('sounds/saath_crore.mp4')
                self.media_player.set_media(media)
                self.media_player.play()

                video_played = True
            except Exception as e:
                print(f"Video error: {str(e)}")
                video_played = False

        # Show trophy image if video failed or sound is muted
        if not video_played:
            try:
                trophy_img = ImageTk.PhotoImage(Image.open("images/trophy.png").resize((150, 150)))
                trophy_label = tk.Label(win_window, image=trophy_img, bg=self.colors['background'])
                trophy_label.image = trophy_img
                trophy_label.pack(pady=20)
            except:
                trophy_label = tk.Label(win_window, text="🏆", font=("Arial", 80),
                                        fg='gold', bg=self.colors['background'])
                trophy_label.pack(pady=20)

        congrats_label = tk.Label(win_window,
                                  text="CONGRATULATIONS!",
                                  font=("Impact", 36, "bold"),
                                  bg=self.colors['background'], fg=self.colors['highlight'])
        congrats_label.pack(pady=10)

        million_label = tk.Label(win_window,
                                 text="$1,000,000",
                                 font=("Arial", 48, "bold"),
                                 bg=self.colors['background'], fg='gold')
        million_label.pack(pady=10)

        buttons_frame = tk.Frame(win_window, bg=self.colors['background'])
        buttons_frame.pack(pady=20)

        play_again_btn = tk.Button(buttons_frame, text="Play Again",
                                   font=("Arial", 14),
                                   bg=self.colors['button_normal'], fg=self.colors['text'],
                                   command=lambda: [self.stop_video(), win_window.destroy(), self.restart_game()])
        play_again_btn.grid(row=0, column=0, padx=10)

        quit_btn = tk.Button(buttons_frame, text="Quit",
                             font=("Arial", 14),
                             bg='#880000', fg='white',
                             command=lambda: [self.stop_video(), win_window.destroy(), self.quit_game()])
        quit_btn.grid(row=0, column=1, padx=10)

        win_window.protocol("WM_DELETE_WINDOW",
                            lambda: [self.stop_video(), self.restore_bg_music_volume(), win_window.destroy()])

    def stop_video(self):
        if hasattr(self, 'media_player'):
            self.media_player.stop()
            self.media_player.release()
            del self.media_player
        if hasattr(self, 'vlc_instance'):
            del self.vlc_instance

        self.restore_bg_music_volume()

    def restart_game(self):
        self.stop_video()

        if PYGAME_AVAILABLE:
            self.bg_channel.stop()
            self.fx_channel.stop()

        self.current_question = 0
        self.lifelines = {'50:50': True, 'Phone': True, 'Ask': True}

        self.fifty_fifty_btn.config(state=tk.NORMAL, bg=self.colors['button_normal'])
        self.phone_btn.config(state=tk.NORMAL, bg=self.colors['button_normal'])
        self.ask_btn.config(state=tk.NORMAL, bg=self.colors['button_normal'])

        self.current_prize_label.config(text="Current Prize: $0")

        self.speech_recognizer.stop()
        if self.mic_icon:
            self.mic_btn.config(image=self.mic_icon)
        else:
            self.mic_btn.config(text="🎤", bg=self.colors['button_normal'])
        self.mic_status_label.config(text="Click to speak", fg=self.colors['text'])

        self.stop_timer()

        self.load_questions_from_file()

        self.bg_music_index = 0
        self.bg_music_playing = False

        self.start_game()

    def quit_game(self):
        self.stop_video()

        # Stop all sounds
        if PYGAME_AVAILABLE:
            pygame.mixer.quit()

        self.speech_recognizer.stop()
        self.root.destroy()

    def play_sound(self, sound_name, volume=0.7):
        if not PYGAME_AVAILABLE or self.sound_muted:
            return

        try:
            sound = pygame.mixer.Sound(self.sounds[sound_name])
            sound.set_volume(volume)

            self.fx_channel.play(sound)

        except Exception as e:
            print(f"Error playing sound {sound_name}: {e}")

    def setup_timer(self):
        self.timer_frame = tk.Frame(self.main_frame, bg=self.colors['background'])
        self.timer_frame.place(relx=0.5, rely=0.82, anchor=tk.CENTER, width=120, height=70)

        # Create canvas for timer
        self.timer_canvas = tk.Canvas(self.timer_frame, width=100, height=70,
                                      bg=self.colors['background'], highlightthickness=0)
        self.timer_canvas.pack(pady=5)

        self.timer_bg = self.timer_canvas.create_arc(10, 10, 90, 90,
                                                     start=0, extent=180,
                                                     fill=self.colors['background'],
                                                     outline=self.colors['highlight'], width=2)

        self.timer_progress = self.timer_canvas.create_arc(10, 10, 90, 90,
                                                           start=0, extent=180,
                                                           fill=self.colors['highlight'],
                                                           outline="")

        self.timer_text = self.timer_canvas.create_text(50, 42, text="",
                                                        font=("Arial", 16, "bold"),
                                                        fill="white")

        self.timer_canvas.tag_raise(self.timer_text)

        # Timer variables
        self.timer_running = False
        self.timer_count = 0
        self.timer_max = 0
        self.timer_id = None

    def start_timer(self, seconds):
        # Stop any existing timer
        self.stop_timer()

        # Set the timer count and start the countdown
        self.timer_count = seconds
        self.timer_max = seconds
        self.timer_canvas.itemconfig(self.timer_text, text=str(seconds))
        self.timer_running = True

        # Make timer visible
        self.timer_frame.place(relx=0.5, rely=0.82, anchor=tk.CENTER, width=120, height=70)

        # Reset progress bar to full
        self.timer_canvas.itemconfig(self.timer_progress, extent=180)

        # Start countdown
        self.update_timer()

        self.timer_canvas.tag_raise(self.timer_text)

    def update_timer(self):
        if not self.timer_running:
            return

        if self.timer_count > 0:
            self.timer_count -= 1
            self.timer_canvas.itemconfig(self.timer_text, text=str(self.timer_count))

            # Update the progress bar
            progress_extent = int(180 * self.timer_count / self.timer_max)
            self.timer_canvas.itemconfig(self.timer_progress, extent=progress_extent)

            # Make timer red when 10 seconds or less remain
            if self.timer_count <= 10:
                self.timer_canvas.itemconfig(self.timer_text, fill="red")

                # Flash the timer background when 5 seconds or less remain
                if self.timer_count <= 5:
                    if self.timer_count % 2 == 0:
                        self.timer_canvas.itemconfig(self.timer_progress, fill=self.colors['highlight'])
                    else:
                        self.timer_canvas.itemconfig(self.timer_progress, fill="#FF0000")  # Red fill
            else:
                self.timer_canvas.itemconfig(self.timer_text, fill="white")

            self.timer_id = self.root.after(1000, self.update_timer)
        else:
            # Time's up
            self.timer_running = False
            self.timer_canvas.itemconfig(self.timer_text, text="0", fill="red")
            self.timer_canvas.itemconfig(self.timer_progress, extent=0)

            # Flash the timer
            for i in range(5):
                self.root.after(300 * i, lambda fill="#FF0000": self.timer_canvas.itemconfig(self.timer_bg, fill=fill))
                self.root.after(300 * i + 150, lambda fill=self.colors['background']:
                self.timer_canvas.itemconfig(self.timer_bg, fill=fill))

            self.root.after(1500, self.times_up)

    def stop_timer(self):
        self.timer_running = False
        if self.timer_id:
            self.root.after_cancel(self.timer_id)
            self.timer_id = None

        self.timer_canvas.itemconfig(self.timer_text, fill="white")
        self.timer_canvas.itemconfig(self.timer_progress, fill=self.colors['highlight'])
        self.timer_canvas.itemconfig(self.timer_bg, fill=self.colors['background'])

    def hide_timer(self):
        self.timer_frame.place_forget()

    def times_up(self):
        if not self.timer_running:
            return
        self.stop_timer()
        self.game_over()

if __name__ == "__main__":
    root = tk.Tk()
    game = MillionaireGame(root)
    root.mainloop()