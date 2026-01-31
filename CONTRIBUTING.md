# FastAPI Backend – Setup Guide 🚀

This repository contains a **FastAPI-based backend API**.
Follow the steps below to set up and run the project locally.

---

## Prerequisites

Ensure you have the following installed:

* **Python 3.10+**
* **Git**
* **pip**

Verify installation:

```bash
python3 --version
git --version
```

---

## 1. Clone the Repository

```bash
git clone https://github.com/your-username/your-repo-name.git
cd your-repo-name
```

---

## 2. Create and Activate a Virtual Environment

Create the virtual environment:

```bash
python3 -m venv venv
```

Activate it:

### Linux / macOS

```bash
source venv/bin/activate
```

### Windows (PowerShell)

```powershell
venv\Scripts\Activate.ps1
```

Once activated, your terminal should show `(venv)`.

---

## 3. Install Dependencies

Upgrade `pip` (recommended):

```bash
pip install --upgrade pip
```

Install the required packages:

```bash
pip install -r requirements.txt
```

---

## 4. Environment Variables

Create a `.env` file in the project root:

```bash
touch .env
```

Example:

```env
ENV=development
DEBUG=True
SECRET_KEY=your-secret-key
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
```

> ⚠️ Do **not** commit `.env` files to version control.

---

## 5. Run the FastAPI Server

Start the development server using **Uvicorn**:

```bash
uvicorn app.main:app --reload
```

* API URL: **[http://127.0.0.1:8000](http://127.0.0.1:8000)**
* Swagger UI: **[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)**
* ReDoc: **[http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)**

---

## 6. Useful Commands

| Command                           | Description              |
| --------------------------------- | ------------------------ |
| `uvicorn app.main:app --reload`   | Start development server |
| `pip install -r requirements.txt` | Install dependencies     |
| `pip install --upgrade pip`       | Upgrade pip              |
| `deactivate`                      | Exit virtual environment |

---

## 7. Troubleshooting

**Dependencies not found?**

* Ensure the virtual environment is activated
* Reinstall requirements

**Server won’t start?**

* Confirm environment variables are set
* Check that the correct Python version is being used