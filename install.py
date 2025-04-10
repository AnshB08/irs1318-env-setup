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


def install_git():
    """Install Git for Windows without package managers"""
    print("Installing Git for Windows...")

    # Create temp directory
    temp_dir = tempfile.mkdtemp()
    git_installer = os.path.join(temp_dir, "git_installer.exe")

    # Latest Git for Windows installer URL
    git_url = "https://github.com/git-for-windows/git/releases/download/v2.41.0.windows.3/Git-2.41.0.3-64-bit.exe"

    # Download the installer
    if not download_file(git_url, git_installer):
        return ("Git", False, "Failed to download Git installer")

    # Run the installer with required parameters
    # /VERYSILENT: No UI during install
    # /NORESTART: Don't restart after installation
    # /NOCANCEL: Disable cancellation during install
    # /COMPONENTS: Select components to install
    # These parameters ensure git.exe is added to PATH
    try:
        print("Running Git installer...")
        install_args = [
            git_installer,
            "/VERYSILENT",
            "/NORESTART",
            "/NOCANCEL",
            "/COMPONENTS=icons,icons\desktop,ext,ext\shellhere,ext\guihere,gitlfs,assoc,assoc_sh",
            "/ADDTOPATH=ALL",  # This adds Git to PATH for all users
        ]

        result = subprocess.run(install_args, capture_output=True, text=True)

        if result.returncode != 0:
            return ("Git", False, f"Installation failed: {result.stderr}")

        # Verify git is in PATH
        try:
            verify = subprocess.run(
                ["git", "--version"], capture_output=True, text=True
            )
            if verify.returncode == 0:
                return ("Git", True, f"Git installed successfully: {verify.stdout}")
            else:
                return ("Git", False, "Git was installed but cannot be found in PATH")
        except FileNotFoundError:
            return ("Git", False, "Git was installed but cannot be found in PATH")

    except Exception as e:
        return ("Git", False, f"Error during Git installation: {str(e)}")
    finally:
        # Clean up temp directory
        try:
            shutil.rmtree(temp_dir)
        except:
            pass


def install_vscode():
    """Install VS Code without package managers"""
    print("Installing Visual Studio Code...")

    # Create temp directory
    temp_dir = tempfile.mkdtemp()
    vscode_installer = os.path.join(temp_dir, "vscode_installer.exe")

    # VS Code System Installer URL (64-bit)
    vscode_url = "https://code.visualstudio.com/sha/download?build=stable&os=win32-x64"

    # Download the installer
    if not download_file(vscode_url, vscode_installer):
        return ("VS Code", False, "Failed to download VS Code installer")

    # Run the installer with required parameters
    try:
        print("Running VS Code installer...")
        # These parameters ensure VS Code is added to PATH
        install_args = [
            vscode_installer,
            "/VERYSILENT",
            "/NORESTART",
            "/MERGETASKS=!runcode,addcontextmenufiles,addcontextmenufolders,associatewithfiles,addtopath",
        ]

        result = subprocess.run(install_args, capture_output=True, text=True)

        if result.returncode != 0:
            return ("VS Code", False, f"Installation failed: {result.stderr}")

        # Verify VS Code is in PATH
        try:
            # Wait a bit to make sure PATH is updated
            import time

            time.sleep(5)

            verify = subprocess.run(
                ["code", "--version"], capture_output=True, text=True
            )
            if verify.returncode == 0:
                return (
                    "VS Code",
                    True,
                    f"VS Code installed successfully: {verify.stdout}",
                )
            else:
                return (
                    "VS Code",
                    False,
                    "VS Code was installed but cannot be found in PATH",
                )
        except FileNotFoundError:
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
            ["uv", "tool", "install", tool], capture_output=True, text=True
        )
        results.append((f"UV tool: {tool}", result.returncode == 0, result.stdout))

    # Update shell
    shell_result = subprocess.run(
        ["uv", "tool", "update-shell"], capture_output=True, text=True
    )
    results.append(
        ("UV update-shell", shell_result.returncode == 0, shell_result.stdout)
    )

    # Configure PDM after all UV tools are installed
    print("Configuring PDM...")
    os.system("pdm config use_uv true")

    # Get Python directory from uv and configure PDM
    uv_python_dir_result = subprocess.run(
        ["uv", "python", "dir"], capture_output=True, text=True
    )
    uv_python_dir = uv_python_dir_result.stdout.strip()
    os.system(f"pdm config python.install_root {uv_python_dir}")

    return (
        "UV Configuration",
        all(r[1] for r in results),
        "\n".join(r[2] for r in results),
    )


def install_single_extension(extension):
    print(f"Installing VS Code extension: {extension}...")
    result = subprocess.run(
        ["code", "--install-extension", extension], capture_output=True, text=True
    )
    return (extension, result.returncode == 0, result.stdout)


def install_vscode_extensions_parallel(extensions):
    print("Installing VS Code extensions in parallel...")
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as extension_executor:
        future_to_ext = {
            extension_executor.submit(install_single_extension, ext): ext
            for ext in extensions
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
        "vscode-icons-team.vscode-icons",
        "ms-python.python",
        "ms-python.vscode-pylance",
        "ms-python.debugpy",
        "ms-python.black-formatter",
        "ms-python.pylint",
        "ms-toolsai.jupyter" "mhutchie.git-graph",
        "visualstudioexptteam.vscodeintellicode",
        "visualstudioexptteam.intellicode-api-usage-examples",
        "christian-kohler.path-intellisense",
        "esbenp.prettier-vscode",
        "dbaeumer.vscode-eslint",
        "ritwickdey.liveserver",
        "xabikos.JavaScriptSnippets",
        "ecmel.vscode-html-css",
        "Zignd.html-css-class-completion",
        "ms-vscode.powershell",
    ]

    # Create a thread pool executor for main installations
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        # Submit installation tasks
        future_to_app = {
            executor.submit(install_git): "Git",
            executor.submit(install_vscode): "VS Code",
            executor.submit(configure_uv): "UV Configuration",
        }

        vscode_completed = False

        # Process results as they complete
        for future in concurrent.futures.as_completed(future_to_app):
            app = future_to_app[future]
            try:
                name, success, output = future.result()
                if success:
                    print(f"✓ {name} completed successfully")
                    if name == "VS Code":
                        vscode_completed = True
                        # Install VS Code extensions as soon as VS Code is ready
                        install_vscode_extensions_parallel(vscode_extensions)
                else:
                    print(f"✗ {name} failed")
                    print(output)
            except Exception as e:
                print(f"✗ {app} generated an exception: {e}")

        # Install VS Code extensions if VS Code installation didn't trigger it
        if not vscode_completed:
            try:
                install_vscode_extensions_parallel(vscode_extensions)
            except Exception as e:
                print(f"✗ VS Code Extensions installation generated an exception: {e}")


if __name__ == "__main__":
    main()
