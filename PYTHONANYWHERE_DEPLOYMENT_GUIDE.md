# 🚀 PythonAnywhere Deployment Guide

Follow these simple steps to deploy **ISL Web Studio** on [PythonAnywhere](https://www.pythonanywhere.com/).

---

## 📋 Step-by-Step Deployment Instructions

### 1. Upload Your Project Files
1. Log in to your [PythonAnywhere Dashboard](https://www.pythonanywhere.com/).
2. Open a **Bash Console** from the **Consoles** tab.
3. Clone your GitHub repository or upload your files into a directory (for example, `/home/yourusername/sign-lan`):
   ```bash
   git clone <YOUR_REPO_URL> sign-lan
   cd sign-lan
   ```

---

### 2. Create and Activate a Virtual Environment
In your PythonAnywhere Bash console, create a Python 3.10 / 3.11 virtual environment and install the dependencies:

```bash
# Create a virtualenv named 'isl-env'
mkvirtualenv isl-env --python=python3.10

# Make sure you are inside the project folder
cd /home/yourusername/sign-lan

# Install dependencies
pip install -r requirements.txt
```

---

### 3. Verify FFmpeg on PythonAnywhere
PythonAnywhere includes `ffmpeg` pre-installed on standard Linux paths (`/usr/bin/ffmpeg`). Verify it in the Bash console:
```bash
ffmpeg -version
```
*(If `ffmpeg` is missing on your free tier instance, install it locally with `pip install imageio-ffmpeg`)*.

---

### 4. Configure the Web App in PythonAnywhere Dashboard

1. Go to the **Web** tab on PythonAnywhere.
2. Click **Add a new web app**.
3. Choose **Manual configuration** (do NOT choose the automatic "Flask" wizard, choose Manual).
4. Select **Python 3.10** (or the matching version of your virtualenv).

#### A. Set Virtualenv Path
In the **Virtualenv** section on the Web tab, enter:
```
/home/yourusername/.virtualenvs/isl-env
```

#### B. Set Working Directory
In the **Code** section:
- **Source code**: `/home/yourusername/sign-lan`
- **Working directory**: `/home/yourusername/sign-lan`

#### C. Configure the WSGI File
Click on the **WSGI configuration file** link (e.g., `/var/www/yourusername_pythonanywhere_com_wsgi.py`).

Delete all default boilerplate code and paste the following:

```python
import sys
import os

# Set path to your project
project_home = '/home/yourusername/sign-lan'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Import the application object
from app import application
```
*(Replace `yourusername` with your actual PythonAnywhere username)*.

Click **Save**.

---

### 5. Configure Static Files (Recommended for Performance)

In the **Static files** section of the **Web** tab:

| URL | Directory |
|---|---|
| `/static/` | `/home/yourusername/sign-lan/static` |

---

### 6. Reload & Launch!

Click the big green **Reload yourusername.pythonanywhere.com** button at the top of the **Web** tab.

Visit your live URL:
👉 **`https://yourusername.pythonanywhere.com`**
