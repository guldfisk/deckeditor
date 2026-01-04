# Project Setup Guide

Follow these steps to set up the development environment on Windows.

## 1. Install pyenv-win
Run PowerShell as **Administrator** and execute the following command to install `pyenv-win`:

```powershell
Invoke-WebRequest -UseBasicParsing -Uri "https://raw.githubusercontent.com/pyenv-win/pyenv-win/master/pyenv-win/install-pyenv-win.ps1" -OutFile "./install-pyenv-win.ps1"; &"./install-pyenv-win.ps1"
```

## 2. Install pipx
Install `pipx` using your global Python environment. 

> **Note:** If you installed Python via the Microsoft Store, replace `py` with `python3` in the command below.

```powershell
py -m pip install --user pipx
```

### Configure PATH for pipx
If you see a warning stating that `pipx.exe` is not on your PATH, navigate to the directory mentioned in the warning (usually `~\AppData\Roaming\Python\Python3x\Scripts`) and run:

```powershell
.\pipx.exe ensurepath
```

**Restart PowerShell** after this step to refresh your environment variables. Verify the installation by typing:

```powershell
pipx
```

## 3. Python Configuration
Install the required Python version and set it as the local version for this project:

```powershell
pyenv install 3.9.13
pyenv local 3.9.13
```

## 4. Virtual Environment
Create and activate a local virtual environment:

```powershell
# Create the environment
python -m venv .venv

# Activate the environment
.\.venv\Scripts\Activate.ps1
```

## 5. Dependency Management (Poetry)
Install Poetry globally via `pipx` and then install the project dependencies:

```powershell
# Install Poetry
pipx install poetry

# Install dependencies from poetry.lock
poetry install
```

## 6. Test-run deckeditor
To simplify this process, you can create a bash script for environment initialization.

```powershell
python -m deckeditor.editor --no-ssl-verify
```
