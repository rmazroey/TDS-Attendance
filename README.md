# TDS-Attendance
This project provides a Django management command to automate the import of attendance data from the **TDS API** into a PostgreSQL database. It extracts and processes student attendance data based on academic year and week number, updating or creating records in the database.

---

## Features
- **Automated Attendance Import** – Downloads and imports attendance data directly from the TDS API.  
- **Dynamic Module Processing** – Retrieves modules for a given academic year and week, fetching attendance data per module.  
- **Upsert Support** – Ensures data integrity by updating existing records or creating new ones if needed.  
- **Flexible Configuration** – Allows filtering by week, year, and report type (`module`).  
- **Batch Processing** – Processes multiple modules and students in one run, reducing manual workload.  
- **Secure Authentication** – Uses environment-based API credentials with base64 encoding for API requests.  

---

## Requirements
- **Python 3.8+**  
- **Django Framework**  
- **PostgreSQL Database**  
- **pipenv** (for dependency management)  
- **TDS API Access**  

---

## Installation

### 1. Clone the Repository  
```bash
git clone https://github.com/yourusername/tds-attendance-import.git
cd tds-attendance-import
