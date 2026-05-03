import hashlib
import random
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import ttk, messagebox

import mysql.connector
from mysql.connector import Error

# =========================================================
# MySQL CONFIGURATION
# Change these values to match your MySQL setup
# =========================================================
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "197319",
    "database": "sorting_visualizer_db",
}

root = None
current_user = ""
current_user_id = None

canvas = None
algo_menu = None
size_scale = None
speed_scale = None
array_entry = None
complexity_label = None
comment_box = None
algo_listbox = None
user_history_box = None
pause_btn = None
username_entry = None
password_entry = None

canvas_width = 900
canvas_height = 380

data = []
original_data = []
is_sorting = False
is_paused = False
generator = None
current_algorithm = None

session_start_time = None
session_algorithms = []

algorithm_steps = {
    "Bubble Sort": [
        "for i <- 0 to n-2",
        "    swapped <- false",
        "    for j <- 0 to n-i-2",
        "        if A[j] > A[j+1]",
        "            swap(A[j], A[j+1])",
        "            swapped <- true",
        "    if swapped = false",
        "        break"
    ],
    "Selection Sort": [
        "for i <- 0 to n-2",
        "    min_index <- i",
        "    for j <- i+1 to n-1",
        "        if A[j] < A[min_index]",
        "            min_index <- j",
        "    swap(A[i], A[min_index])"
    ],
    "Insertion Sort": [
        "for i <- 1 to n-1",
        "    key <- A[i]",
        "    j <- i-1",
        "    while j >= 0 and A[j] > key",
        "        A[j+1] <- A[j]",
        "        j <- j-1",
        "    A[j+1] <- key"
    ],
    "Quick Sort": [
        "quickSort(low, high)",
        "    if low < high",
        "        pivot <- A[high]",
        "        partition array around pivot",
        "        place pivot in correct position",
        "        quickSort(low, pi-1)",
        "        quickSort(pi+1, high)"
    ],
    "Heap Sort": [
        "build max heap",
        "for i <- n-1 down to 1",
        "    swap(A[0], A[i])",
        "    reduce heap size",
        "    heapify(root)",
        "heapify(i)",
        "    compare parent with children",
        "    swap with larger child if needed"
    ]
}


# =========================================================
# DATABASE HELPERS
# =========================================================
def get_server_connection(with_database=True):
    config = DB_CONFIG.copy()
    if not with_database:
        config.pop("database", None)
    return mysql.connector.connect(**config)


def initialize_database():
    try:
        server_conn = get_server_connection(with_database=False)
        server_cursor = server_conn.cursor()
        server_cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{DB_CONFIG['database']}` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        server_cursor.close()
        server_conn.close()

        conn = get_server_connection(with_database=True)
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(100) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                last_login DATETIME NULL,
                last_algorithm VARCHAR(100) DEFAULT 'None',
                total_logins INT DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS recent_arrays (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                array_text TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS session_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                login_time DATETIME NOT NULL,
                logout_time DATETIME NULL,
                duration_seconds INT DEFAULT 0,
                duration_text VARCHAR(50) DEFAULT '0s',
                algorithms VARCHAR(255) NOT NULL DEFAULT 'None',
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )

        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Error as e:
        messagebox.showerror(
            "Database Error",
            "MySQL connection failed.\n\n"
            f"Error: {e}\n\n"
            "Check your MySQL server and DB_CONFIG values at the top of the file."
        )
        return False


def execute_query(query, params=None, fetchone=False, fetchall=False, commit=False):
    conn = None
    cursor = None
    try:
        conn = get_server_connection(with_database=True)
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params or ())

        result = None
        if fetchone:
            result = cursor.fetchone()
        elif fetchall:
            result = cursor.fetchall()

        if commit:
            conn.commit()
            if cursor.lastrowid:
                return cursor.lastrowid

        return result
    except Error as e:
        messagebox.showerror("Database Error", f"MySQL query failed:\n{e}")
        return None
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# =========================================================
# USER / SESSION HELPERS
# =========================================================
def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def user_exists(username):
    row = execute_query(
        "SELECT id FROM users WHERE username = %s",
        (username,),
        fetchone=True,
    )
    return row is not None


def create_user(username, password):
    return execute_query(
        """
        INSERT INTO users (username, password_hash, last_algorithm, total_logins)
        VALUES (%s, %s, 'None', 0)
        """,
        (username, hash_password(password)),
        commit=True,
    )


def verify_user(username, password):
    row = execute_query(
        "SELECT * FROM users WHERE username = %s",
        (username,),
        fetchone=True,
    )
    if not row:
        return None
    if row["password_hash"] != hash_password(password):
        return None
    return row


def update_login(user_id):
    now = datetime.now()
    execute_query(
        """
        UPDATE users
        SET last_login = %s, total_logins = total_logins + 1
        WHERE id = %s
        """,
        (now, user_id),
        commit=True,
    )


def update_last_algorithm(user_id, algorithm):
    global session_algorithms

    execute_query(
        "UPDATE users SET last_algorithm = %s WHERE id = %s",
        (algorithm, user_id),
        commit=True,
    )

    if algorithm and algorithm not in session_algorithms:
        session_algorithms.append(algorithm)


def add_custom_array(user_id, arr):
    array_text = ", ".join(map(str, arr))
    execute_query(
        "INSERT INTO recent_arrays (user_id, array_text) VALUES (%s, %s)",
        (user_id, array_text),
        commit=True,
    )

    old_rows = execute_query(
        """
        SELECT id FROM recent_arrays
        WHERE user_id = %s
        ORDER BY created_at DESC, id DESC
        """,
        (user_id,),
        fetchall=True,
    )

    if old_rows and len(old_rows) > 3:
        ids_to_delete = [str(row["id"]) for row in old_rows[3:]]
        placeholders = ", ".join(["%s"] * len(ids_to_delete))
        execute_query(
            f"DELETE FROM recent_arrays WHERE id IN ({placeholders})",
            tuple(ids_to_delete),
            commit=True,
        )


def parse_array_text(array_text):
    text = array_text.replace(",", " ").strip()
    if not text:
        return []
    return [int(x) for x in text.split()]


def get_user(user_id):
    if not user_id:
        return {}

    user = execute_query(
        "SELECT * FROM users WHERE id = %s",
        (user_id,),
        fetchone=True,
    )
    if not user:
        return {}

    arrays = execute_query(
        """
        SELECT array_text FROM recent_arrays
        WHERE user_id = %s
        ORDER BY created_at DESC, id DESC
        LIMIT 3
        """,
        (user_id,),
        fetchall=True,
    ) or []

    user["recent_arrays"] = [parse_array_text(row["array_text"]) for row in arrays]
    return user


def make_duration_text(total_seconds):
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    if hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    if minutes > 0:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


def save_session(user_id):
    global session_start_time, session_algorithms

    if not user_id or session_start_time is None:
        return

    logout_dt = datetime.now()
    duration_seconds = max(0, int((logout_dt - session_start_time).total_seconds()))
    algorithms_text = ", ".join(session_algorithms) if session_algorithms else "None"

    execute_query(
        """
        INSERT INTO session_history (
            user_id, login_time, logout_time,
            duration_seconds, duration_text, algorithms
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            user_id,
            session_start_time,
            logout_dt,
            duration_seconds,
            make_duration_text(duration_seconds),
            algorithms_text,
        ),
        commit=True,
    )

    session_start_time = None
    session_algorithms = []


def get_weekly_history(user_id):
    rows = []
    if not user_id:
        return rows

    week_ago = datetime.now() - timedelta(days=7)

    db_rows = execute_query(
        """
        SELECT login_time, logout_time, duration_seconds, duration_text, algorithms
        FROM session_history
        WHERE user_id = %s AND login_time >= %s
        ORDER BY login_time DESC
        """,
        (user_id, week_ago),
        fetchall=True,
    ) or []

    for item in db_rows:
        rows.append({
            "login_time": item["login_time"].strftime("%Y-%m-%d %H:%M:%S") if item["login_time"] else "",
            "logout_time": item["logout_time"].strftime("%Y-%m-%d %H:%M:%S") if item["logout_time"] else "",
            "duration_seconds": item["duration_seconds"] or 0,
            "duration_text": item["duration_text"] or "0s",
            "algorithms": item["algorithms"] or "None",
        })

    if user_id == current_user_id and session_start_time is not None:
        now = datetime.now()
        duration_seconds = max(0, int((now - session_start_time).total_seconds()))
        rows.insert(0, {
            "login_time": session_start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "logout_time": "Active now",
            "duration_seconds": duration_seconds,
            "duration_text": make_duration_text(duration_seconds),
            "algorithms": ", ".join(session_algorithms) if session_algorithms else "None",
        })

    return rows


# =========================================================
# UI HELPERS
# =========================================================
def open_user_history_window():
    weekly_rows = get_weekly_history(current_user_id)

    history_window = tk.Toplevel(root)
    history_window.title(f"{current_user} - Weekly User History")
    history_window.config(bg="#1e1e1e")
    history_window.resizable(True, True)

    root.update_idletasks()
    width = 1000
    height = 430
    x = root.winfo_x() + 70
    y = root.winfo_y() + 70
    history_window.geometry(f"{width}x{height}+{x}+{y}")

    tk.Label(
        history_window,
        text=f"Weekly User History - {current_user}",
        font=("Arial", 16, "bold"),
        bg="#1e1e1e",
        fg="white"
    ).pack(pady=(12, 4))

    tk.Label(
        history_window,
        text="Showing the last 7 days of sessions",
        font=("Arial", 10),
        bg="#1e1e1e",
        fg="#cccccc"
    ).pack(pady=(0, 10))

    table_frame = tk.Frame(history_window, bg="#1e1e1e", padx=12, pady=10)
    table_frame.pack(fill="both", expand=True)

    style = ttk.Style(history_window)
    style.theme_use("clam")
    style.configure(
        "History.Treeview",
        background="#111111",
        fieldbackground="#111111",
        foreground="white",
        rowheight=30,
        font=("Arial", 10)
    )
    style.configure(
        "History.Treeview.Heading",
        background="#2b2b2b",
        foreground="white",
        font=("Arial", 10, "bold")
    )
    style.map(
        "History.Treeview",
        background=[("selected", "#00bcd4")],
        foreground=[("selected", "black")]
    )

    columns = ("login", "logout", "duration", "algorithms")
    tree = ttk.Treeview(
        table_frame,
        columns=columns,
        show="headings",
        style="History.Treeview"
    )

    tree.heading("login", text="Login Time")
    tree.heading("logout", text="Logout Time")
    tree.heading("duration", text="Used Time")
    tree.heading("algorithms", text="Sorting Algorithm(s)")

    tree.column("login", width=190, anchor="center")
    tree.column("logout", width=190, anchor="center")
    tree.column("duration", width=120, anchor="center")
    tree.column("algorithms", width=420, anchor="w")

    y_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
    x_scroll = ttk.Scrollbar(table_frame, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)

    tree.grid(row=0, column=0, sticky="nsew")
    y_scroll.grid(row=0, column=1, sticky="ns")
    x_scroll.grid(row=1, column=0, sticky="ew")

    table_frame.grid_rowconfigure(0, weight=1)
    table_frame.grid_columnconfigure(0, weight=1)

    if weekly_rows:
        for row in weekly_rows:
            tree.insert(
                "",
                tk.END,
                values=(
                    row.get("login_time", ""),
                    row.get("logout_time", ""),
                    row.get("duration_text", ""),
                    row.get("algorithms", "")
                )
            )
    else:
        tree.insert("", tk.END, values=("No data found in last 7 days", "", "", ""))


def clear_root():
    for widget in root.winfo_children():
        widget.destroy()


def show_login_screen():
    global username_entry, password_entry

    clear_root()
    root.title("Sorting Visualizer - Login")
    root.config(bg="#1e1e1e")
    root.geometry("560x450")
    root.minsize(560, 450)
    root.resizable(False, False)

    main = tk.Frame(root, bg="#1e1e1e", padx=30, pady=20)
    main.pack(expand=True, fill="both")

    title = tk.Label(
        main,
        text="Sorting Visualizer Login",
        font=("Arial", 20, "bold"),
        bg="#1e1e1e",
        fg="white",
    )
    title.pack(pady=(20, 25))

    form = tk.Frame(main, bg="#2b2b2b", padx=25, pady=25)
    form.pack(fill="x", pady=(0, 15))

    tk.Label(
        form,
        text="Username",
        font=("Arial", 11, "bold"),
        bg="#2b2b2b",
        fg="white",
    ).pack(anchor="w", pady=(0, 6))

    username_entry = tk.Entry(form, font=("Arial", 12), width=30)
    username_entry.pack(fill="x", pady=(0, 14))

    tk.Label(
        form,
        text="Password",
        font=("Arial", 11, "bold"),
        bg="#2b2b2b",
        fg="white",
    ).pack(anchor="w", pady=(0, 6))

    password_entry = tk.Entry(form, font=("Arial", 12), width=30, show="*")
    password_entry.pack(fill="x", pady=(0, 18))
    password_entry.bind("<Return>", lambda event: login())

    btn_frame = tk.Frame(form, bg="#2b2b2b")
    btn_frame.pack(fill="x")

    tk.Button(
        btn_frame,
        text="Login",
        command=login,
        font=("Arial", 11, "bold"),
        bg="#4caf50",
        fg="white",
        relief=tk.FLAT,
        width=12,
        cursor="hand2",
    ).pack(side="left", padx=(0, 10))

    tk.Button(
        btn_frame,
        text="Sign Up",
        command=signup,
        font=("Arial", 11, "bold"),
        bg="#00bcd4",
        fg="black",
        relief=tk.FLAT,
        width=12,
        cursor="hand2",
    ).pack(side="left")

    tk.Label(
        main,
        text="Create an account or log in to continue.",
        font=("Arial", 10),
        bg="#1e1e1e",
        fg="#cccccc",
    ).pack(pady=(8, 12))


def signup():
    username = username_entry.get().strip()
    password = password_entry.get().strip()

    if not username or not password:
        messagebox.showerror("Error", "Username and password cannot be empty.")
        return

    if len(username) < 3:
        messagebox.showerror("Error", "Username must be at least 3 characters.")
        return

    if len(password) < 4:
        messagebox.showerror("Error", "Password must be at least 4 characters.")
        return

    if user_exists(username):
        messagebox.showerror("Error", "This username already exists.")
        return

    create_user(username, password)
    messagebox.showinfo("Success", "Account created successfully. Now log in.")


def login():
    global current_user, current_user_id, session_start_time, session_algorithms

    username = username_entry.get().strip()
    password = password_entry.get().strip()

    if not username or not password:
        messagebox.showerror("Error", "Please enter username and password.")
        return

    user = verify_user(username, password)
    if not user:
        messagebox.showerror("Error", "Invalid username or password.")
        return

    current_user = user["username"]
    current_user_id = user["id"]
    session_start_time = datetime.now()
    session_algorithms = []

    update_login(current_user_id)
    show_visualizer_screen()


def show_visualizer_screen():
    global canvas, algo_menu, size_scale, speed_scale, array_entry
    global complexity_label, comment_box, algo_listbox
    global user_history_box, pause_btn, canvas_width, canvas_height
    global data, original_data, is_sorting, is_paused, generator, current_algorithm

    clear_root()
    root.title("Sorting Algorithm Visualizer")
    root.config(bg="#1e1e1e")
    root.state("zoomed")
    root.resizable(True, True)

    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    canvas_width = max(650, min(950, screen_width - 500))
    canvas_height = max(280, min(420, screen_height - 430))

    data = []
    original_data = []
    is_sorting = False
    is_paused = False
    generator = None
    current_algorithm = None

    root.grid_rowconfigure(1, weight=1)
    root.grid_columnconfigure(0, weight=1)

    control_frame = tk.Frame(root, bg="#2b2b2b", padx=10, pady=10)
    control_frame.grid(row=0, column=0, sticky="ew")
    control_frame.grid_columnconfigure(8, weight=1)

    header_frame = tk.Frame(control_frame, bg="#2b2b2b")
    header_frame.grid(row=0, column=0, columnspan=9, sticky="ew", pady=(0, 12))
    header_frame.grid_columnconfigure(0, weight=1)

    tk.Label(
        header_frame,
        text="Sorting Algorithm Visualizer",
        font=("Arial", 18, "bold"),
        bg="#2b2b2b",
        fg="white"
    ).grid(row=0, column=0, sticky="w")

    tk.Button(
        header_frame,
        text="User History",
        command=open_user_history_window,
        width=12,
        font=("Arial", 10, "bold"),
        bg="#8e44ad",
        fg="white",
        relief=tk.FLAT,
        cursor="hand2"
    ).grid(row=0, column=1, padx=(0, 10))

    tk.Button(
        header_frame,
        text="Logout",
        command=logout,
        width=10,
        font=("Arial", 10, "bold"),
        bg="#607d8b",
        fg="white",
        relief=tk.FLAT,
        cursor="hand2"
    ).grid(row=0, column=2, padx=(0, 12))

    tk.Label(
        header_frame,
        text=f"Welcome, {current_user}",
        font=("Arial", 11, "bold"),
        bg="#2b2b2b",
        fg="#9fd3ff"
    ).grid(row=0, column=3, sticky="e")

    tk.Label(control_frame, text="Algorithm:", font=("Arial", 11, "bold"), bg="#2b2b2b", fg="white").grid(row=1, column=0, padx=5, pady=5)

    algo_menu = ttk.Combobox(
        control_frame,
        values=["Bubble Sort", "Selection Sort", "Insertion Sort", "Quick Sort", "Heap Sort"],
        state="readonly",
        width=18,
        font=("Arial", 11)
    )
    algo_menu.grid(row=1, column=1, padx=5, pady=5)
    algo_menu.current(0)
    algo_menu.bind("<<ComboboxSelected>>", on_algorithm_change)

    tk.Label(control_frame, text="Size:", font=("Arial", 11, "bold"), bg="#2b2b2b", fg="white").grid(row=1, column=2, padx=5, pady=5)

    size_scale = tk.Scale(
        control_frame,
        from_=5, to=60,
        orient=tk.HORIZONTAL,
        length=180,
        bg="#2b2b2b",
        fg="white",
        highlightthickness=0,
        troughcolor="#444444",
        activebackground="#00bcd4",
        font=("Arial", 10)
    )
    size_scale.set(20)
    size_scale.grid(row=1, column=3, padx=5, pady=5)

    tk.Label(control_frame, text="Speed:", font=("Arial", 11, "bold"), bg="#2b2b2b", fg="white").grid(row=1, column=4, padx=5, pady=5)

    speed_scale = tk.Scale(
        control_frame,
        from_=1, to=20,
        orient=tk.HORIZONTAL,
        length=180,
        bg="#2b2b2b",
        fg="white",
        highlightthickness=0,
        troughcolor="#444444",
        activebackground="#00bcd4",
        font=("Arial", 10)
    )
    speed_scale.set(8)
    speed_scale.grid(row=1, column=5, padx=5, pady=5)

    tk.Button(control_frame, text="Generate", command=generate_data, width=12, font=("Arial", 11, "bold"), bg="#00bcd4", fg="black", relief=tk.FLAT, cursor="hand2").grid(row=1, column=6, padx=8, pady=5)
    tk.Button(control_frame, text="Start", command=start_sorting, width=12, font=("Arial", 11, "bold"), bg="#4caf50", fg="white", relief=tk.FLAT, cursor="hand2").grid(row=1, column=7, padx=8, pady=5)

    pause_btn = tk.Button(control_frame, text="Pause", command=pause_resume_sorting, width=12, font=("Arial", 11, "bold"), bg="#ff9800", fg="white", relief=tk.FLAT, cursor="hand2")
    pause_btn.grid(row=2, column=6, padx=8, pady=8)

    tk.Button(control_frame, text="Reset", command=reset_sorting, width=12, font=("Arial", 11, "bold"), bg="#f44336", fg="white", relief=tk.FLAT, cursor="hand2").grid(row=2, column=7, padx=8, pady=8)

    tk.Label(control_frame, text="Custom Array:", font=("Arial", 11, "bold"), bg="#2b2b2b", fg="white").grid(row=3, column=0, padx=5, pady=10, sticky="w")

    array_entry = tk.Entry(control_frame, width=55, font=("Arial", 11))
    array_entry.grid(row=3, column=1, columnspan=4, padx=5, pady=10, sticky="w")
    array_entry.insert(0, "5, 2, 9, 1, 7")

    tk.Button(control_frame, text="Use Custom Array", command=use_custom_array, width=18, font=("Arial", 11, "bold"), bg="#9c27b0", fg="white", relief=tk.FLAT, cursor="hand2").grid(row=3, column=6, columnspan=2, padx=8, pady=10)

    tk.Label(
        control_frame,
        text="Enter numbers separated by comma or space. Example: 5, 2, 9, 1, 7",
        font=("Arial", 9),
        bg="#2b2b2b",
        fg="#cccccc"
    ).grid(row=4, column=0, columnspan=8, pady=(0, 5), sticky="w")

    main_frame = tk.Frame(root, bg="#1e1e1e")
    main_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))
    main_frame.grid_rowconfigure(0, weight=1)
    main_frame.grid_columnconfigure(0, weight=3)
    main_frame.grid_columnconfigure(1, weight=1)

    left_frame = tk.Frame(main_frame, bg="#1e1e1e")
    left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
    left_frame.grid_rowconfigure(0, weight=1)
    left_frame.grid_columnconfigure(0, weight=1)

    right_frame = tk.Frame(main_frame, bg="#1e1e1e")
    right_frame.grid(row=0, column=1, sticky="nsew")
    right_frame.grid_columnconfigure(0, weight=1)

    canvas = tk.Canvas(left_frame, width=canvas_width, height=canvas_height, bg="white", bd=0, highlightthickness=0)
    canvas.grid(row=0, column=0, sticky="nsew")

    complexity_label = tk.Label(left_frame, text="Time Complexity: ", font=("Arial", 12, "bold"), bg="#1e1e1e", fg="#00e676")
    complexity_label.grid(row=1, column=0, pady=8)

    legend_frame = tk.Frame(left_frame, bg="#1e1e1e")
    legend_frame.grid(row=2, column=0, pady=5)
    create_legend(legend_frame, "#3498db", "Normal", 0)
    create_legend(legend_frame, "#e74c3c", "Comparing", 1)
    create_legend(legend_frame, "#f1c40f", "Current / Key / Swap", 2)
    create_legend(legend_frame, "#2ecc71", "Sorted", 3)

    tk.Label(right_frame, text="Algorithm Steps (Pseudo Code)", font=("Arial", 13, "bold"), bg="#1e1e1e", fg="white").pack(pady=(0, 4), anchor="n")

    algo_listbox = tk.Listbox(
        right_frame,
        width=38,
        height=10,
        font=("Consolas", 12),
        bg="#111111",
        fg="white",
        selectbackground="#f1c40f",
        selectforeground="black",
        activestyle="none",
        bd=2,
        relief="solid"
    )
    algo_listbox.pack(fill="x", pady=(0, 8))

    tk.Label(right_frame, text="Step Explanation", font=("Arial", 12, "bold"), bg="#1e1e1e", fg="white").pack(pady=(0, 3), anchor="n")

    comment_box = tk.Text(
        right_frame,
        height=6,
        width=38,
        font=("Consolas", 11),
        bg="#111111",
        fg="#f5f5f5",
        wrap="word",
        bd=2,
        relief="solid"
    )
    comment_box.pack(fill="x")
    comment_box.insert(tk.END, "Comments will appear here during sorting.\n")
    comment_box.config(state="disabled")

    tk.Label(right_frame, text="User Summary", font=("Arial", 12, "bold"), bg="#1e1e1e", fg="white").pack(pady=(12, 3), anchor="n")

    user_history_box = tk.Text(
        right_frame,
        height=7,
        width=38,
        font=("Consolas", 10),
        bg="#111111",
        fg="#9fd3ff",
        wrap="word",
        bd=2,
        relief="solid"
    )
    user_history_box.pack(fill="both", expand=True)
    user_history_box.config(state="disabled")

    update_algorithm_display()
    load_user_preferences()
    generate_data()
    update_user_summary()


def logout():
    global is_sorting, generator, current_user, current_user_id

    user_id_to_save = current_user_id
    save_session(user_id_to_save)

    is_sorting = False
    generator = None
    current_user = ""
    current_user_id = None
    root.state("normal")
    show_login_screen()


def create_legend(parent, color, text, col):
    box = tk.Label(parent, bg=color, width=2, height=1)
    box.grid(row=0, column=col * 2, padx=(10, 3))
    label = tk.Label(parent, text=text, bg="#1e1e1e", fg="white", font=("Arial", 10))
    label.grid(row=0, column=col * 2 + 1, padx=(0, 10))


def write_comment(message):
    comment_box.config(state="normal")
    comment_box.delete("1.0", tk.END)
    comment_box.insert(tk.END, message)
    comment_box.config(state="disabled")


def update_algorithm_display():
    algo = algo_menu.get()
    algo_listbox.delete(0, tk.END)
    for step in algorithm_steps[algo]:
        algo_listbox.insert(tk.END, step)


def highlight_step(index):
    algo_listbox.selection_clear(0, tk.END)
    if 0 <= index < algo_listbox.size():
        algo_listbox.selection_set(index)
        algo_listbox.activate(index)
        algo_listbox.see(index)


def on_algorithm_change(event=None):
    if not is_sorting:
        update_algorithm_display()
        highlight_step(-1)
        write_comment(
            f"{algo_menu.get()} selected.\n"
            "Pseudo-code is shown above.\n"
            "When sorting starts, the current line will be highlighted."
        )


def load_user_preferences():
    user = get_user(current_user_id)
    last_algo = user.get("last_algorithm", "None")
    if last_algo in algo_menu["values"]:
        algo_menu.set(last_algo)
        update_algorithm_display()

    arrays = user.get("recent_arrays", [])
    if arrays:
        latest = arrays[0]
        array_entry.delete(0, tk.END)
        array_entry.insert(0, ", ".join(map(str, latest)))


def update_user_summary():
    user = get_user(current_user_id)
    recent_arrays = user.get("recent_arrays", [])

    last_login = user.get("last_login")
    if last_login:
        if isinstance(last_login, datetime):
            last_login_text = last_login.strftime("%Y-%m-%d %H:%M:%S")
        else:
            last_login_text = str(last_login)
    else:
        last_login_text = "Never"

    lines = [
        f"Username      : {current_user}",
        f"Last login    : {last_login_text}",
        f"Last algorithm: {user.get('last_algorithm', 'None')}",
        f"Total logins  : {user.get('total_logins', 0)}",
        "",
        "Recent custom arrays:"
    ]

    if recent_arrays:
        for idx, arr in enumerate(recent_arrays, start=1):
            lines.append(f"{idx}. {arr}")
    else:
        lines.append("No custom arrays saved yet.")

    user_history_box.config(state="normal")
    user_history_box.delete("1.0", tk.END)
    user_history_box.insert(tk.END, "\n".join(lines))
    user_history_box.config(state="disabled")


def parse_custom_array(text):
    text = text.strip()
    if not text:
        raise ValueError("Input is empty.")

    text = text.replace(",", " ")
    parts = text.split()

    if len(parts) < 2:
        raise ValueError("Please enter at least 2 numbers.")

    numbers = [int(part) for part in parts]

    if len(numbers) > 60:
        raise ValueError("Maximum 60 numbers allowed.")

    return numbers


def use_custom_array():
    global data, original_data

    if is_sorting:
        return

    try:
        values = parse_custom_array(array_entry.get())
        data = values
        original_data = data[:]
        size_scale.set(len(data))
        add_custom_array(current_user_id, values)
        draw_data()
        complexity_label.config(text="Time Complexity: ")
        highlight_step(-1)
        write_comment(
            f"Custom array loaded:\n{data}\n"
            "Now choose an algorithm and press Start."
        )
        update_user_summary()
    except ValueError as e:
        messagebox.showerror("Invalid Input", str(e))
        write_comment(
            "Invalid custom array input.\n"
            "Use integers separated by comma or space.\n"
            "Example: 5, 2, 9, 1, 7"
        )


def generate_data():
    global data, original_data

    if is_sorting:
        return

    size = size_scale.get()
    data = [random.randint(20, 390) for _ in range(size)]
    original_data = data[:]
    draw_data()
    complexity_label.config(text="Time Complexity: ")
    highlight_step(-1)
    write_comment(
        "A new random array was created.\n"
        "Blue bars are unsorted values.\n"
        "Choose an algorithm and press Start."
    )


def draw_data(color_array=None):
    canvas.delete("all")

    if not data:
        return

    n = len(data)
    bar_width = canvas_width / n
    max_value = max(data)

    if color_array is None:
        color_array = ["#3498db"] * n

    for i, value in enumerate(data):
        x1 = i * bar_width + 2
        y1 = canvas_height - (value / max_value) * (canvas_height - 40)
        x2 = (i + 1) * bar_width - 2
        y2 = canvas_height

        canvas.create_rectangle(x1, y1, x2, y2, fill=color_array[i], outline="")

        if n <= 30:
            canvas.create_text(
                x1 + (bar_width / 2),
                y1 - 10,
                text=str(value),
                font=("Arial", 9, "bold"),
                fill="black"
            )

    root.update_idletasks()


def get_delay():
    speed = speed_scale.get()
    return 1200 - (speed * 50)


def start_sorting():
    global is_sorting, is_paused, generator, current_algorithm

    if is_sorting or not data:
        return

    is_sorting = True
    is_paused = False
    pause_btn.config(text="Pause")
    current_algorithm = algo_menu.get()
    update_algorithm_display()
    update_last_algorithm(current_user_id, current_algorithm)
    update_user_summary()

    if current_algorithm == "Bubble Sort":
        generator = bubble_sort()
        complexity_label.config(text="Time Complexity: O(n²)")
    elif current_algorithm == "Selection Sort":
        generator = selection_sort()
        complexity_label.config(text="Time Complexity: O(n²)")
    elif current_algorithm == "Insertion Sort":
        generator = insertion_sort()
        complexity_label.config(text="Time Complexity: O(n²)")
    elif current_algorithm == "Quick Sort":
        generator = quick_sort()
        complexity_label.config(text="Time Complexity: Average O(n log n), Worst O(n²)")
    elif current_algorithm == "Heap Sort":
        generator = heap_sort()
        complexity_label.config(text="Time Complexity: O(n log n)")

    write_comment(
        f"{current_algorithm} started.\n"
        "Watch the pseudo-code highlight on the right side."
    )
    animate()


def animate():
    global is_sorting, generator

    if not is_sorting:
        return

    if is_paused:
        root.after(100, animate)
        return

    try:
        next(generator)
        root.after(get_delay(), animate)
    except StopIteration:
        is_sorting = False
        generator = None
        draw_data(["#2ecc71"] * len(data))
        highlight_step(-1)
        write_comment(
            f"{current_algorithm} completed.\n"
            "All bars are now green, so the array is fully sorted."
        )


def pause_resume_sorting():
    global is_paused

    if not is_sorting:
        return

    is_paused = not is_paused

    if is_paused:
        pause_btn.config(text="Resume")
        write_comment(
            "Sorting is paused.\n"
            "Press Resume to continue from the current step."
        )
    else:
        pause_btn.config(text="Pause")
        write_comment(
            f"{current_algorithm} resumed.\n"
            "The highlighted pseudo-code line will continue updating."
        )


def reset_sorting():
    global is_sorting, is_paused, generator, data

    is_sorting = False
    is_paused = False
    generator = None
    pause_btn.config(text="Pause")

    if original_data:
        data = original_data[:]
        draw_data()
        highlight_step(-1)
        write_comment(
            f"Array reset:\n{data}\n"
            "You can start sorting again."
        )
    else:
        generate_data()


def bubble_sort():
    n = len(data)

    for i in range(n):
        highlight_step(0)
        swapped = False
        yield

        highlight_step(1)
        write_comment(
            f"Bubble Sort:\n"
            f"Start pass {i + 1}.\n"
            "Set swapped = false before comparing adjacent elements."
        )
        yield

        for j in range(0, n - i - 1):
            highlight_step(2)
            write_comment(
                f"Bubble Sort:\n"
                f"Loop j from 0 to {n - i - 2}.\n"
                f"Current j = {j}."
            )
            yield

            highlight_step(3)
            colors = ["#3498db"] * n
            colors[j] = "#e74c3c"
            colors[j + 1] = "#e74c3c"
            for k in range(n - i, n):
                colors[k] = "#2ecc71"
            draw_data(colors)

            write_comment(
                f"Bubble Sort:\n"
                f"Check if A[{j}] = {data[j]} > A[{j + 1}] = {data[j + 1]}."
            )
            yield

            if data[j] > data[j + 1]:
                highlight_step(4)
                data[j], data[j + 1] = data[j + 1], data[j]

                colors = ["#3498db"] * n
                colors[j] = "#f1c40f"
                colors[j + 1] = "#f1c40f"
                for k in range(n - i, n):
                    colors[k] = "#2ecc71"
                draw_data(colors)

                write_comment(
                    f"Bubble Sort:\n"
                    f"Swapped A[{j}] and A[{j + 1}] because left value was greater."
                )
                yield

                highlight_step(5)
                swapped = True
                write_comment(
                    "Bubble Sort:\n"
                    "Set swapped = true because a swap happened in this pass."
                )
                yield

        highlight_step(6)
        colors = ["#3498db"] * n
        for k in range(n - i - 1, n):
            colors[k] = "#2ecc71"
        draw_data(colors)

        write_comment(
            "Bubble Sort:\n"
            "Check if swapped = false.\n"
            "If no swap happened, the array is already sorted."
        )
        yield

        if not swapped:
            highlight_step(7)
            draw_data(["#2ecc71"] * n)
            write_comment(
                "Bubble Sort:\n"
                "Break the loop because the array is already sorted."
            )
            yield
            return


def selection_sort():
    n = len(data)

    for i in range(n - 1):
        highlight_step(0)
        write_comment(
            f"Selection Sort:\n"
            f"Start outer loop with i = {i}."
        )
        yield

        highlight_step(1)
        min_idx = i
        colors = ["#3498db"] * n
        for k in range(i):
            colors[k] = "#2ecc71"
        colors[min_idx] = "#f1c40f"
        draw_data(colors)

        write_comment(
            f"Selection Sort:\n"
            f"Set min_index = {i}.\n"
            f"Current minimum is A[{min_idx}] = {data[min_idx]}."
        )
        yield

        for j in range(i + 1, n):
            highlight_step(2)
            colors = ["#3498db"] * n
            for k in range(i):
                colors[k] = "#2ecc71"
            colors[min_idx] = "#f1c40f"
            colors[j] = "#e74c3c"
            draw_data(colors)

            write_comment(
                f"Selection Sort:\n"
                f"Check next element in inner loop: j = {j}."
            )
            yield

            highlight_step(3)
            write_comment(
                f"Selection Sort:\n"
                f"Check if A[{j}] = {data[j]} < A[{min_idx}] = {data[min_idx]}."
            )
            yield

            if data[j] < data[min_idx]:
                highlight_step(4)
                min_idx = j

                colors = ["#3498db"] * n
                for k in range(i):
                    colors[k] = "#2ecc71"
                colors[min_idx] = "#f1c40f"
                draw_data(colors)

                write_comment(
                    f"Selection Sort:\n"
                    f"Update min_index to {min_idx} because a smaller value was found."
                )
                yield

        highlight_step(5)
        data[i], data[min_idx] = data[min_idx], data[i]

        colors = ["#3498db"] * n
        for k in range(i + 1):
            colors[k] = "#2ecc71"
        draw_data(colors)

        write_comment(
            f"Selection Sort:\n"
            f"Swap A[{i}] with A[{min_idx}] to place the minimum in correct position."
        )
        yield


def insertion_sort():
    n = len(data)

    for i in range(1, n):
        highlight_step(0)
        write_comment(
            f"Insertion Sort:\n"
            f"Start outer loop with i = {i}."
        )
        yield

        highlight_step(1)
        key = data[i]
        colors = ["#3498db"] * n
        for k in range(i):
            colors[k] = "#2ecc71"
        colors[i] = "#f1c40f"
        draw_data(colors)

        write_comment(
            f"Insertion Sort:\n"
            f"Set key = A[{i}] = {key}."
        )
        yield

        highlight_step(2)
        j = i - 1
        write_comment(
            f"Insertion Sort:\n"
            f"Set j = i - 1 = {j}."
        )
        yield

        while j >= 0 and data[j] > key:
            highlight_step(3)
            colors = ["#3498db"] * n
            for k in range(j):
                colors[k] = "#2ecc71"
            colors[j] = "#e74c3c"
            colors[j + 1] = "#f1c40f"
            draw_data(colors)

            write_comment(
                f"Insertion Sort:\n"
                f"Check while condition: j >= 0 and A[{j}] = {data[j]} > key = {key}."
            )
            yield

            highlight_step(4)
            data[j + 1] = data[j]
            draw_data(colors)

            write_comment(
                f"Insertion Sort:\n"
                f"Shift A[{j}] to A[{j + 1}]."
            )
            yield

            highlight_step(5)
            j = j - 1
            write_comment(
                f"Insertion Sort:\n"
                f"Decrease j by 1. Now j = {j}."
            )
            yield

        highlight_step(6)
        data[j + 1] = key

        colors = ["#3498db"] * n
        for k in range(i + 1):
            colors[k] = "#2ecc71"
        draw_data(colors)

        write_comment(
            f"Insertion Sort:\n"
            f"Insert key at A[{j + 1}].\n"
            f"Now first {i + 1} elements are sorted."
        )
        yield


def quick_sort():
    if len(data) <= 1:
        return
    yield from quick_sort_recursive(0, len(data) - 1)


def quick_sort_recursive(low, high):
    highlight_step(0)
    write_comment(
        f"Quick Sort:\n"
        f"Call quickSort({low}, {high})."
    )
    yield

    highlight_step(1)
    if low < high:
        write_comment(
            f"Quick Sort:\n"
            f"Since {low} < {high}, continue sorting this part."
        )
        yield

        pi = yield from partition(low, high)

        highlight_step(5)
        write_comment(
            f"Quick Sort:\n"
            f"Sort left part: {low} to {pi - 1}."
        )
        yield
        yield from quick_sort_recursive(low, pi - 1)

        highlight_step(6)
        write_comment(
            f"Quick Sort:\n"
            f"Sort right part: {pi + 1} to {high}."
        )
        yield
        yield from quick_sort_recursive(pi + 1, high)
    else:
        colors = ["#3498db"] * len(data)
        if 0 <= low < len(data):
            colors[low] = "#2ecc71"
        draw_data(colors)
        write_comment(
            f"Quick Sort:\n"
            f"This part has size 0 or 1, so it is already sorted."
        )
        yield


def partition(low, high):
    highlight_step(2)
    pivot = data[high]
    colors = ["#3498db"] * len(data)
    colors[high] = "#f1c40f"
    draw_data(colors)
    write_comment(
        f"Quick Sort:\n"
        f"Choose pivot = A[{high}] = {pivot}."
    )
    yield

    i = low - 1
    for j in range(low, high):
        highlight_step(3)
        colors = ["#3498db"] * len(data)
        colors[high] = "#f1c40f"
        colors[j] = "#e74c3c"
        if i >= low:
            colors[i] = "#2ecc71"
        draw_data(colors)
        write_comment(
            f"Quick Sort:\n"
            f"Compare A[{j}] = {data[j]} with pivot = {pivot}."
        )
        yield

        if data[j] <= pivot:
            i += 1
            data[i], data[j] = data[j], data[i]
            colors = ["#3498db"] * len(data)
            colors[high] = "#f1c40f"
            colors[i] = "#2ecc71"
            colors[j] = "#2ecc71"
            draw_data(colors)
            write_comment(
                f"Quick Sort:\n"
                f"A[{j}] is not greater than pivot, so swap it into the left part."
            )
            yield

    highlight_step(4)
    data[i + 1], data[high] = data[high], data[i + 1]
    colors = ["#3498db"] * len(data)
    colors[i + 1] = "#2ecc71"
    draw_data(colors)
    write_comment(
        f"Quick Sort:\n"
        f"Place pivot {pivot} at index {i + 1}. Now pivot is in correct position."
    )
    yield
    return i + 1


def heap_sort():
    n = len(data)
    if n <= 1:
        return

    highlight_step(0)
    write_comment(
        "Heap Sort:\n"
        "Start by building a max heap."
    )
    yield

    for i in range(n // 2 - 1, -1, -1):
        yield from heapify(n, i)

    for end in range(n - 1, 0, -1):
        highlight_step(1)
        colors = ["#3498db"] * n
        colors[0] = "#f1c40f"
        colors[end] = "#f1c40f"
        draw_data(colors)
        write_comment(
            f"Heap Sort:\n"
            f"Swap root A[0] = {data[0]} with A[{end}] = {data[end]}."
        )
        yield

        highlight_step(2)
        data[0], data[end] = data[end], data[0]
        colors = ["#3498db"] * n
        for k in range(end, n):
            colors[k] = "#2ecc71"
        colors[0] = "#f1c40f"
        draw_data(colors)
        write_comment(
            f"Heap Sort:\n"
            f"Largest value moved to index {end}."
        )
        yield

        highlight_step(3)
        write_comment(
            f"Heap Sort:\n"
            f"Reduce heap size to {end} and heapify the root again."
        )
        yield

        highlight_step(4)
        yield from heapify(end, 0)


def heapify(n, i):
    highlight_step(5)
    largest = i
    left = 2 * i + 1
    right = 2 * i + 2

    colors = ["#3498db"] * len(data)
    if i < len(data):
        colors[i] = "#f1c40f"
    if left < n:
        colors[left] = "#e74c3c"
    if right < n:
        colors[right] = "#e74c3c"
    draw_data(colors)
    write_comment(
        f"Heap Sort:\n"
        f"Heapify node {i}. Compare parent with left child {left} and right child {right}."
    )
    yield

    highlight_step(6)
    if left < n and data[left] > data[largest]:
        largest = left
    if right < n and data[right] > data[largest]:
        largest = right

    write_comment(
        f"Heap Sort:\n"
        f"Find the largest among parent and children. Largest index is {largest}."
    )
    yield

    if largest != i:
        highlight_step(7)
        data[i], data[largest] = data[largest], data[i]
        colors = ["#3498db"] * len(data)
        colors[i] = "#f1c40f"
        colors[largest] = "#f1c40f"
        draw_data(colors)
        write_comment(
            f"Heap Sort:\n"
            f"Swap A[{i}] with A[{largest}] to restore max heap property."
        )
        yield
        yield from heapify(n, largest)


def on_app_close():
    save_session(current_user_id)
    root.destroy()


# =========================================================
# MAIN
# =========================================================
root = tk.Tk()

if initialize_database():
    root.protocol("WM_DELETE_WINDOW", on_app_close)
    show_login_screen()
    root.mainloop()
else:
    root.destroy()
