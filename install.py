import subprocess
import concurrent.futures
import os
import sys
import tempfile
import urllib.request
import shutil
import winreg
import ctypes
from pathlib import Path
import re
import json
import time


def refresh_path():
    """Refresh the PATH environment variable during runtime"""

    ps_command = (
        '$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine")'
        ' + ";" +'
        '[System.Environment]::GetEnvironmentVariable("Path","User")'
    )
    subprocess.run(["powershell", "-Command", ps_command])


def is_admin():
    """Check if the script is running with admin privileges"""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except:
        return False


def download_file(url, path):
    """Download a file from URL to the specified path"""
    print(f"Downloading {url} to {path}...")
    try:
        with urllib.request.urlopen(url) as response, open(path, "wb") as out_file:
            shutil.copyfileobj(response, out_file)
        return True
    except Exception as e:
        print(f"Failed to download {url}: {e}")
        return False


def test_git():
    try:
        verify = subprocess.run(
            ["powershell", "git", "--version"], capture_output=True, text=True
        )
        if verify.returncode == 0:
            return True
        else:
            return False
    except Exception as e:
        print(f"Unable to verify Git install: {str(e)}")
        return False


def install_git():
    """Install Git for Windows without package managers"""
    print("Installing Git for Windows...")

    if test_git():
        return ("Git", False, "Git is already installed")

    # Create temp directory
    temp_dir = tempfile.mkdtemp()
    installer_path = os.path.join(temp_dir, "git_installer.exe")

    def get_git_url():
        latest_release = (
            "https://api.github.com/repos/git-for-windows/git/releases/latest"
        )
        try:
            with urllib.request.urlopen(latest_release) as response:
                assets = json.load(response)["assets"]
                for asset in assets:
                    if re.match(r"Git-\d*\.\d*\.\d*-64-bit\.exe", asset["name"]):
                        return asset["browser_download_url"]
        except Exception as e:
            print(f"Failed to retrieve latest Git install url: {str(e)}")
            return None

    # Get latest Git install url for Windows 64 bit systems
    git_url = get_git_url()

    if git_url is None:
        return ("Git", False, "Failed to retrieve latest Git install url")

    # Download the installer
    if not download_file(git_url, installer_path):
        return ("Git", False, "Failed to download Git installer")

    # Run installer
    try:
        print("Running Git installer...")
        install_args = [
            "powershell",
            installer_path,
            "/VERYSILENT",
            "/NORESTART",
            "/NOCANCEL",
            "/COMPONENTS=icons,gitlfs,windowsterminal,scalar",
            "/EDITOROPTION=VisualStudioCode",
            "/DEFAULTBRANCHNAME=main",
        ]

        result = subprocess.run(install_args, capture_output=True, text=True)

        if result.returncode != 0:
            return ("Git", False, f"Installation failed: {result.stderr}")

        # Verify git is in PATH

        refresh_path()

        if test_git():
            return ("Git", True, f"Git installed successfully")
        else:
            return ("Git", False, "Git was installed but cannot be found in PATH")

    except Exception as e:
        return ("Git", False, f"Error during Git installation: {str(e)}")
    finally:
        # Clean up temp directory
        try:
            shutil.rmtree(temp_dir)
        except:
            pass


def test_vscode():
    # winerror 2 caused by code not being in path
    try:
        verify = subprocess.run(
            ["powershell", "code", "--version"], capture_output=True, text=True
        )
        if verify.returncode == 0:
            return True
        else:
            return False
    except Exception as e:
        print(f"Unable to verify VS Code install: {e}")
        return False


def install_vscode():
    """Install VS Code without package managers"""
    print("Installing Visual Studio Code...")

    if test_vscode():
        return ("VS Code", False, "VS Code is already installed")

    # Create temp directory
    temp_dir = tempfile.mkdtemp()
    installer_path = os.path.join(temp_dir, "vscode_installer.exe")

    # VS Code System Installer URL (64-bit)
    vscode_url = "https://code.visualstudio.com/sha/download?build=stable&os=win32-x64"

    # Download the installer
    if not download_file(vscode_url, installer_path):
        return ("VS Code", False, "Failed to download VS Code installer")

    # Run installer
    try:
        print("Running VS Code installer...")
        # These parameters ensure VS Code is added to PATH
        install_args = [
            "powershell",
            installer_path,
            "/VERYSILENT",
            "/MERGETASKS=!runcode",
        ]

        result = subprocess.run(install_args, capture_output=True, text=True)

        if result.returncode != 0:
            return ("VS Code", False, f"Installation failed: {result.stderr}")

        # Verify VS Code is in PATH

        refresh_path()

        if test_vscode():
            return (
                "VS Code",
                True,
                f"VS Code installed successfully",
            )
        else:
            return (
                "VS Code",
                False,
                "VS Code was installed but cannot be found in PATH",
            )
    except Exception as e:
        return ("VS Code", False, f"Error during VS Code installation: {str(e)}")
    finally:
        # Clean up temp directory
        try:
            shutil.rmtree(temp_dir)
        except:
            pass


def configure_uv():
    print("Configuring UV...")

    # UV tools to install
    uv_tools = ["pdm", "black", "flake8", "mypy", "jupyterlab"]
    results = []

    for tool in uv_tools:
        print(f"Installing {tool} with UV...")
        result = subprocess.run(
            ["powershell", "uv", "tool", "install", tool],
            capture_output=True,
            text=True,
        )
        results.append((f"UV tool: {tool}", result.returncode == 0, result.stdout))

    # Update shell
    shell_result = subprocess.run(
        ["powershell", "uv", "tool", "update-shell"], capture_output=True, text=True
    )
    results.append(
        ("UV update-shell", shell_result.returncode == 0, shell_result.stdout)
    )

    # Configure PDM after all UV tools are installed
    print("Configuring PDM...")
    os.system("powershell pdm config use_uv true")

    # Get Python directory from uv and configure PDM
    uv_python_dir_result = subprocess.run(
        ["powershell", "uv", "python", "dir"], capture_output=True, text=False
    )
    uv_python_dir = uv_python_dir_result.stdout.strip().decode()
    os.system(f"powershell pdm config python.install_root {uv_python_dir}")

    return (
        "UV Configuration",
        all(r[1] for r in results),
        "\n".join(r[2] for r in results),
    )


def install_extension(extension):
    print(f"Installing VS Code extension: {extension}...")
    attempt = 0

    while True:
        attempt += 1
        result = subprocess.run(
            ["powershell", "code", "--install-extension", extension],
            capture_output=True,
            text=True,
        )

        if result.returncode == 1 or attempt > 3:
            break

        # wait 1 sec before trying again
        time.sleep(1)

    return (extension, result.returncode == 0, result.stdout)


def install_vscode_extensions_parallel(extensions):
    print("Installing VS Code extensions in parallel...")
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as extension_executor:
        future_to_ext = {
            extension_executor.submit(install_extension, ext): ext for ext in extensions
        }

        for future in concurrent.futures.as_completed(future_to_ext):
            ext = future_to_ext[future]
            try:
                name, success, output = future.result()
                results.append((f"Extension: {name}", success, output))
                if success:
                    print(f"✓ Extension {name} installed successfully")
                else:
                    print(f"✗ Extension {name} installation failed")
            except Exception as e:
                print(f"✗ Extension {ext} generated an exception: {e}")
                results.append((f"Extension: {ext}", False, str(e)))

    return (
        "VS Code Extensions",
        all(r[1] for r in results),
        "\n".join(r[2] for r in results),
    )


def main():
    # Check for administrator privileges
    if not is_admin():
        print("This script requires administrator privileges for proper installation.")
        print("Please run this script as administrator.")
        return

    print("Starting parallel installations...")

    # List of VS Code extensions
    vscode_extensions = [
        "ms-python.python",
        "vscode-icons-team.vscode-icons",
        "mhutchie.git-graph",
        "visualstudioexptteam.vscodeintellicode",
        "christian-kohler.path-intellisense",
        "esbenp.prettier-vscode",
        "dbaeumer.vscode-eslint",
        "ritwickdey.liveserver",
        "xabikos.JavaScriptSnippets",
        "ecmel.vscode-html-css",
        "Zignd.html-css-class-completion",
        "ms-toolsai.jupyter",
        "visualstudioexptteam.intellicode-api-usage-examples",
        "ms-python.pylint",
        "ms-python.black-formatter",
        "ms-vscode.powershell",
        "ms-python.debugpy",
        "ms-python.vscode-pylance",
    ]

    # Create a thread pool executor for main installations
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        # Submit installation tasks
        future_to_app = {
            executor.submit(install_git): "Git",
            executor.submit(install_vscode): "VS Code",
            executor.submit(configure_uv): "UV Configuration",
        }

        # Process results as they complete
        for future in concurrent.futures.as_completed(future_to_app):
            app = future_to_app[future]
            try:
                name, success, output = future.result()
                if success:
                    print(f"✓ {name} completed successfully")
                else:
                    print(f"✗ {name} failed")
                    print(output)
            except Exception as e:
                print(f"✗ {app} generated an exception: {e}")

        # Install VS Code extensions
        if test_vscode():
            try:
                install_vscode_extensions_parallel(vscode_extensions)
            except Exception as e:
                print(
                    f"✗ VS Code Extensions installation generated an exception: {str(e)}"
                )
        else:
            print("Unable to verify VS Code install, not installing extensions")

        ps_command = (
            '$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine")'
            ' + ";" +'
            '[System.Environment]::GetEnvironmentVariable("Path","User")'
        )
        subprocess.run(["powershell", "-Command", ps_command])

        print("Restart terminal")


if __name__ == "__main__":
    main()
