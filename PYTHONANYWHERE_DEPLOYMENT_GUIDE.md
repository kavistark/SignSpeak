# 🚀 PythonAnywhere Deployment Guide (Django)

Follow these simple steps to deploy **ISL Web Studio (SignSpeak)** on [PythonAnywhere](https://www.pythonanywhere.com/).

---

## 📋 Step-by-Step Deployment Instructions

### 1. Upload Your Project Files
1. Log in to your [PythonAnywhere Dashboard](https://www.pythonanywhere.com/).
2. Open a **Bash Console** from the **Consoles** tab.
3. Clone your GitHub repository or upload your files into `/home/yourusername/SignSpeak`:
   ```bash
   git clone <YOUR_REPO_URL> SignSpeak
   cd SignSpeak
   ```

---

### 2. Create and Activate a Virtual Environment
In your PythonAnywhere Bash console, create a Python 3.10 virtual environment and install the dependencies:

```bash
# Create a virtualenv named 'isl-env'
mkvirtualenv isl-env --python=python3.10

# Go to your project folder
cd /home/yourusername/SignSpeak

# Install dependencies (use headless opencv on Linux servers)
pip install -r requirements.txt
pip uninstall opencv-python -y
pip install opencv-python-headless
```

---

### 3. Run Django Migrations & Collect Static
In the Bash console:
```bash
python manage.py migrate
```

---

### 4. Configure the Web App in PythonAnywhere Dashboard

1. Go to the **Web** tab on PythonAnywhere.
2. Click **Add a new web app**.
3. Choose **Manual configuration** (select **Python 3.10**).

#### A. Set Virtualenv Path
In the **Virtualenv** section on the Web tab, enter:
```
/home/yourusername/.virtualenvs/isl-env
```

#### B. Set Working Directory & Source Code
In the **Code** section:
- **Source code**: `/home/yourusername/SignSpeak`
- **Working directory**: `/home/yourusername/SignSpeak`

#### C. Configure the WSGI File
Click on the **WSGI configuration file** link (e.g., `/var/www/yourusername_pythonanywhere_com_wsgi.py`).

Delete all default code and replace it with:

```python
import os
import sys

# Path to your project directory
path = '/home/yourusername/SignSpeak'
if path not in sys.path:
    sys.path.insert(0, path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'signspeak.settings'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```
*(Replace `yourusername` with your actual PythonAnywhere username, e.g. `nconixtechnology`)*.

Click **Save**.

---

### 5. Configure Static Files

In the **Static files** section of the **Web** tab:

| URL | Directory |
|---|---|
| `/static/` | `/home/yourusername/SignSpeak/static` |

---

### 6. Reload & Launch!

Click the big green **Reload yourusername.pythonanywhere.com** button at the top of the **Web** tab.

Visit your live URL:
👉 **`https://yourusername.pythonanywhere.com`**
