
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "hospital.db"


def get_connection():
    """Connect to the hospital SQLite database."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create all hospital database tables."""

    with get_connection() as conn:

        # Patients
        conn.execute("""
            CREATE TABLE IF NOT EXISTS patients (
                patient_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                age INTEGER NOT NULL,
                phone TEXT NOT NULL,
                email TEXT,
                disease TEXT,
                blood_group TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Patient medical history
        conn.execute("""
            CREATE TABLE IF NOT EXISTS medical_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id TEXT NOT NULL,
                record TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (patient_id)
                    REFERENCES patients(patient_id)
            )
        """)

        # Doctors
        conn.execute("""
            CREATE TABLE IF NOT EXISTS doctors (
                doctor_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                specialization TEXT NOT NULL,
                experience INTEGER NOT NULL,
                is_available INTEGER NOT NULL DEFAULT 1,
                consultation_fee REAL NOT NULL DEFAULT 0
            )
        """)

        # Appointments
        conn.execute("""
            CREATE TABLE IF NOT EXISTS appointments (
                appointment_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                doctor_id TEXT NOT NULL,
                appointment_date TEXT NOT NULL,
                appointment_time TEXT NOT NULL,
                appointment_type TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Scheduled',
                FOREIGN KEY (patient_id)
                    REFERENCES patients(patient_id),
                FOREIGN KEY (doctor_id)
                    REFERENCES doctors(doctor_id)
            )
        """)

        # Emergency queue records
        conn.execute("""
            CREATE TABLE IF NOT EXISTS emergency_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id TEXT NOT NULL,
                priority_level INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'Waiting',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (patient_id)
                    REFERENCES patients(patient_id)
            )
        """)

        # Rooms
        conn.execute("""
            CREATE TABLE IF NOT EXISTS rooms (
                room_number INTEGER PRIMARY KEY,
                room_type TEXT NOT NULL,
                price_per_day REAL NOT NULL,
                is_available INTEGER NOT NULL DEFAULT 1,
                patient_id TEXT,
                FOREIGN KEY (patient_id)
                    REFERENCES patients(patient_id)
            )
        """)

        # Room release history
        conn.execute("""
            CREATE TABLE IF NOT EXISTS room_releases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_number INTEGER NOT NULL,
                patient_id TEXT NOT NULL,
                days INTEGER NOT NULL,
                charge REAL NOT NULL,
                released_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (room_number)
                    REFERENCES rooms(room_number),
                FOREIGN KEY (patient_id)
                    REFERENCES patients(patient_id)
            )
        """)
        # Medicines given to patients
        conn.execute("""
            CREATE TABLE IF NOT EXISTS medicine_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id TEXT NOT NULL,
                medicine_name TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                price_per_unit REAL NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (patient_id)
                    REFERENCES patients(patient_id)
            )
        """)
        # Bills
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bills (
                bill_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL UNIQUE,
                consultation REAL NOT NULL DEFAULT 0,
                treatment REAL NOT NULL DEFAULT 0,
                medicine REAL NOT NULL DEFAULT 0,
                room REAL NOT NULL DEFAULT 0,
                emergency REAL NOT NULL DEFAULT 0,
                insurance REAL NOT NULL DEFAULT 0,
                paid REAL NOT NULL DEFAULT 0,
                FOREIGN KEY (patient_id)
                    REFERENCES patients(patient_id)
            )
        """)

        # Individual payments
        conn.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bill_id TEXT NOT NULL,
                amount REAL NOT NULL,
                paid_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (bill_id)
                    REFERENCES bills(bill_id)
            )
        """)

        # Patient discharge
        conn.execute("""
            CREATE TABLE IF NOT EXISTS discharges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id TEXT NOT NULL UNIQUE,
                treatment_completed INTEGER NOT NULL,
                doctor_approval INTEGER NOT NULL,
                discharged_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (patient_id)
                    REFERENCES patients(patient_id)
            )
        """)


if __name__ == "__main__":
    init_db()
    print("Hospital database tables are ready.")
    print(f"Database path: {DATABASE_PATH}")
