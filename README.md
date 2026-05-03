# Sorting Algorithm Visualizer

A desktop-based **Sorting Algorithm Visualizer** built with **Python** and **Tkinter**. This project helps students understand how sorting algorithms work internally by showing comparisons, swaps, current steps, pseudo-code, and time complexity through animated bars.

The project was developed as an educational tool for learning Data Structures and Algorithms (DSA), especially sorting algorithms.

---

## Table of Contents

- [Project Overview](#project-overview)
- [Features](#features)
- [Sorting Algorithms](#sorting-algorithms)
- [Technologies Used](#technologies-used)
- [System Requirements](#system-requirements)
- [Project Files](#project-files)
- [Installation](#installation)
- [MySQL Database Setup](#mysql-database-setup)
- [How to Run](#how-to-run)
- [How to Use the App](#how-to-use-the-app)
- [Database Tables](#database-tables)
- [Color Legend](#color-legend)
- [Future Improvements](#future-improvements)
- [Team Members](#team-members)
- [References](#references)

---

## Project Overview

Learning sorting algorithms only from code or theory can be difficult because students cannot clearly see how comparisons, swaps, and recursive steps happen. This application solves that problem by visualizing sorting algorithms in real time.

Users can generate random arrays, enter custom arrays, choose a sorting algorithm, control animation speed, pause/resume sorting, reset the array, and view pseudo-code with step-by-step explanations.

The project also includes a user login system and user history tracking.

---

## Features

- Desktop GUI application using Python Tkinter
- User login and signup system
- Password hashing using SHA-256
- Random array generation
- Custom array input
- Sorting animation using vertical bars
- Speed control slider
- Size control slider
- Pause and resume sorting
- Reset array option
- Pseudo-code display for each algorithm
- Highlighted current pseudo-code step
- Step-by-step explanation box
- Time complexity display
- User summary panel
- Stores last used sorting algorithm
- Stores last 3 custom arrays
- Weekly user history table
- Tracks login time, logout time, used time, and algorithms used
- MySQL database support

---

## Sorting Algorithms

The application currently supports:

1. Bubble Sort
2. Selection Sort
3. Insertion Sort
4. Quick Sort
5. Heap Sort

### Time Complexities

| Algorithm | Time Complexity |
|---|---|
| Bubble Sort | O(n²) |
| Selection Sort | O(n²) |
| Insertion Sort | O(n²) |
| Quick Sort | Average O(n log n), Worst O(n²) |
| Heap Sort | O(n log n) |

---

## Technologies Used

- **Programming Language:** Python
- **GUI Framework:** Tkinter
- **Database:** MySQL
- **Database Connector:** mysql-connector-python
- **Password Security:** hashlib SHA-256
- **IDE:** PyCharm / VS Code

---

## System Requirements

### Hardware Requirements

- Minimum 4 GB RAM
- Intel Core i3 / AMD equivalent processor
- Keyboard and mouse
- Standard desktop or laptop display

### Software Requirements

- Windows or Linux operating system
- Python 3.x
- Tkinter library
- MySQL Server
- mysql-connector-python package
- Code editor such as PyCharm or VS Code

---

## Project Files

Recommended file structure:

```text
Sorting-Algorithm-Visualizer/
│
├── sorting_visualizer_mysql.py   # Main MySQL version of the project
├── final_v2.py                   # JSON-based version, optional
├── README.md                     # Project documentation
└── users.json                    # Auto-created only in JSON version
```

---

## Installation

### 1. Install Python

Download and install Python 3 from the official Python website.

Check Python installation:

```bash
python --version
```

or:

```bash
python3 --version
```

### 2. Install Required Package

For the MySQL version, install the MySQL connector:

```bash
pip install mysql-connector-python
```

For Linux, if Tkinter is missing, install it using:

```bash
sudo apt install python3-tk
```

---

## MySQL Database Setup

The MySQL version uses this file:

```bash
sorting_visualizer_mysql.py
```

At the top of the file, update the database configuration according to your MySQL setup:

```python
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "your_mysql_password",
    "database": "sorting_visualizer_db",
}
```

The program automatically creates the database and required tables if the MySQL connection is correct.

### Important

Do not share your real MySQL password publicly. Change the password value before running the project on another computer.

---

## How to Run

### Run MySQL Version

Open terminal or command prompt in the project folder and run:

```bash
python sorting_visualizer_mysql.py
```

or:

```bash
python3 sorting_visualizer_mysql.py
```

### Run JSON Version

If you do not want to use MySQL, you can run the JSON version:

```bash
python final_v2.py
```

The JSON version stores user data in a local `users.json` file.

---

## How to Use the App

1. Open the application.
2. Create a new account using the **Sign Up** button.
3. Log in with your username and password.
4. Choose a sorting algorithm from the dropdown menu.
5. Generate a random array using the **Generate** button.
6. Or enter your own numbers in the custom array field.
7. Click **Use Custom Array** if you entered custom values.
8. Click **Start** to begin visualization.
9. Use **Pause** to stop temporarily.
10. Use **Resume** to continue sorting.
11. Use **Reset** to return to the original array.
12. Click **User History** to view weekly usage history.
13. Click **Logout** to save the current session.

---

## Database Tables

The MySQL version creates three main tables:

### 1. users

Stores user account information.

| Column | Purpose |
|---|---|
| id | Unique user ID |
| username | User login name |
| password_hash | Hashed password |
| last_login | Last login time |
| last_algorithm | Last used sorting algorithm |
| total_logins | Total number of logins |
| created_at | Account creation time |

### 2. recent_arrays

Stores the user's recent custom arrays.

| Column | Purpose |
|---|---|
| id | Unique array record ID |
| user_id | Connected user ID |
| array_text | Custom array values |
| created_at | Array creation time |

Only the latest 3 custom arrays are kept for each user.

### 3. session_history

Stores user session history.

| Column | Purpose |
|---|---|
| id | Unique session ID |
| user_id | Connected user ID |
| login_time | Login time |
| logout_time | Logout time |
| duration_seconds | Total used time in seconds |
| duration_text | Readable used time |
| algorithms | Algorithms used during the session |

---

## Color Legend

| Color | Meaning |
|---|---|
| Blue | Normal unsorted element |
| Red | Comparing elements |
| Yellow | Current, key, pivot, or swap element |
| Green | Sorted element |

---

## Future Improvements

- Add Merge Sort again
- Add side-by-side algorithm comparison
- Add graph for time complexity comparison
- Add manual step-by-step execution mode
- Add sound effect for swaps
- Add export option for user history
- Convert the desktop app into a web application
- Build an executable `.exe` file for easy installation

---

## Team Members

| ID | Name | Intake/Section |
|---|---|---|
| 20244103117 | Sayem Islam Leon | 54/3 |
| 20244103085 | Samira Ibrahim | 54/3 |
| 20244103083 | Billah | 54/3 |
| 20244103103 | Musfiq | 54/3 |
| 20244103115 | Farjana Shanjida Shinzu | 54/3 |

---

## References

- VisuAlgo: https://visualgo.net
- Algorithm Visualizer: https://algorithm-visualizer.org
- Cormen, Thomas H., et al. *Introduction to Algorithms*. 3rd ed., MIT Press, 2009.
- Sedgewick, Robert, and Kevin Wayne. *Algorithms*. 4th ed., Addison-Wesley, 2011.

---

## License

This project is created for academic and educational purposes.
