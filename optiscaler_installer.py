import os
import shutil
import zipfile
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

import requests  # Make sure dependency_manager.py ensures this is present

class OptiScalerInstaller:
    """
    Handles downloading, extraction, backup, installation, configuration, and uninstallation of OptiScaler.
    """
    def __init__(self, config_dir: Path, fsr_manager, steam_utils):
        self.config_dir = config_dir
        self.fsr_manager = fsr_manager
        self.steam_utils = steam_utils
        self.installs_file = self.config_dir / "installations.json"
        self.github_api_url = "https://api.github.com/repos/optiscaler/OptiScaler/releases"

    def download_latest_nightly(self) -> Optional[str]:
        """
        Download the latest OptiScaler nightly or stable release from GitHub.
        Returns the path to the downloaded archive.
        """
        try:
            response = requests.get(self.github_api_url)
            response.raise_for_status()
            releases = response.json()
            for release in releases:
                if release.get("prerelease", False) or release.get("tag_name") == "nightly":
                    for asset in release["assets"]:
                        if asset["name"].endswith((".zip", ".7z")):
                            download_url = asset["browser_download_url"]
                            filename = asset["name"]
                            print(f"Downloading {filename}...")
                            zip_response = requests.get(download_url)
                            zip_response.raise_for_status()
                            download_path = self.config_dir / filename
                            with open(download_path, "wb") as f:
                                f.write(zip_response.content)
                            return str(download_path)
            # If no nightly found, try latest stable release
            if releases:
                latest_release = releases[0]
                for asset in latest_release["assets"]:
                    if asset["name"].endswith((".zip", ".7z")):
                        download_url = asset["browser_download_url"]
                        filename = asset["name"]
                        print(f"No nightly found, downloading latest stable: {filename}...")
                        zip_response = requests.get(download_url)
                        zip_response.raise_for_status()
                        download_path = self.config_dir / filename
                        with open(download_path, "wb") as f:
                            f.write(zip_response.content)
                        return str(download_path)
            print("No releases found")
            return None
        except Exception as e:
            print(f"Error downloading build: {e}")
            return None

    def extract_optiscaler(self, archive_path: str, target_dir: str) -> bool:
        """
        Extracts OptiScaler archive (.zip or .7z) into the specified directory.
        """
        try:
            archive_file = Path(archive_path)
            if archive_file.suffix.lower() == '.7z':
                result = subprocess.run(['7z', 'x', archive_path, f'-o{target_dir}', '-y'],
                                       capture_output=True, text=True)
                if result.returncode != 0:
                    print(f"7z extraction failed: {result.stderr}")
                    return False
            else:
                with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                    zip_ref.extractall(target_dir)
            return True
        except FileNotFoundError:
            print("7z command not found. Please install p7zip: sudo pacman -S p7zip")
            return False
        except Exception as e:
            print(f"Error extracting OptiScaler: {e}")
            return False

    def backup_original_files(self, target_dir: str) -> Dict[str, str]:
        """
        Backup game upscaling DLLs before overwriting them.
        Returns a map of original file name to backup path.
        """
        backup_map = {}
        target_path = Path(target_dir)
        files_to_backup = [
            "nvngx.dll", "libxess.dll", "amd_fidelityfx_fsr2.dll",
            "amd_fidelityfx_fsr3.dll", "ffx_fsr2_api_x64.dll"
        ]
        for filename in files_to_backup:
            original_file = target_path / filename
            if original_file.exists():
                backup_file = target_path / f"{filename}.optiscaler_backup"
                shutil.copy2(original_file, backup_file)
                backup_map[filename] = str(backup_file)
        return backup_map

    def install_optiscaler(self, game_info: Dict, exe_location: Dict, zip_path: str) -> bool:
        """
        Installs OptiScaler into the selected game's executable directory.
        """
        target_dir = Path(exe_location["path"])
        print(f"Installing OptiScaler to: {target_dir}")
        print(f"Target executable: {exe_location['exe_name']}")
        print(f"Location type: {exe_location['type']}")
        backup_map = self.backup_original_files(str(target_dir))
        if not self.extract_optiscaler(zip_path, str(target_dir)):
            return False
        setup_bat = target_dir / "OptiScaler Setup.bat"
        if setup_bat.exists():
            try:
                subprocess.run(["wine", str(setup_bat)], cwd=str(target_dir), check=True)
                print("Windows setup completed successfully")
            except subprocess.CalledProcessError:
                print("Windows auto-setup failed, proceeding with Linux setup")
        self.run_optiscaler_setup(str(target_dir))
        self.configure_optiscaler_ini(str(target_dir))
        # FSR4 DLL to compatdata (if possible)
        compatdata_path = self.steam_utils.get_compatdata_path(game_info["app_id"])
        fsr4_dll_copied = False
        if compatdata_path:
            fsr4_dll_copied = self.fsr_manager.copy_fsr4_dll_to_compatdata(game_info["app_id"], compatdata_path)
        install_info = {
            "game": game_info,
            "install_path": str(target_dir),
            "exe_location": exe_location,
            "timestamp": datetime.now().isoformat(),
            "backup_files": backup_map,
            "zip_source": zip_path,
            "fsr4_dll_copied": fsr4_dll_copied
        }
        self.save_installation(install_info)
        return True

    def run_optiscaler_setup(self, install_dir: str):
        """
        Runs the OptiScaler Linux setup script in a terminal.
        """
        install_path = Path(install_dir)
        setup_scripts = [
            install_path / "setup_linux.sh",
            install_path / "OptiScaler Setup.sh",
            install_path / "setup.sh"
        ]
        for setup_script in setup_scripts:
            if setup_script.exists():
                try:
                    print(f"Found OptiScaler setup script: {setup_script.name}")
                    setup_script.chmod(0o755)
                    print("Opening interactive setup window...")
                    print("Please configure your OptiScaler settings in the terminal window that opens.")
                    print(f"Running setup script in directory: {install_path}")
                    terminals = [
                        ["konsole", "--workdir", str(install_path), "-e", str(setup_script)],
                        ["gnome-terminal", "--working-directory", str(install_path), "--", str(setup_script)],
                        ["xfce4-terminal", "--working-directory", str(install_path), "-e", str(setup_script)],
                        ["alacritty", "--working-directory", str(install_path), "-e", str(setup_script)],
                        ["kitty", "--directory", str(install_path), str(setup_script)],
                        ["terminator", "--working-directory", str(install_path), "-e", str(setup_script)],
                        ["xterm", "-e", f"cd '{install_path}' && {setup_script}"]
                    ]
                    script_launched = False
                    for terminal_cmd in terminals:
                        try:
                            subprocess.run(["which", terminal_cmd[0]], capture_output=True, check=True)
                            subprocess.Popen(terminal_cmd)
                            print(f"Launched setup script in {terminal_cmd[0]}")
                            script_launched = True
                            input("\nPress Enter after you have completed the OptiScaler setup...")
                            break
                        except (subprocess.CalledProcessError, FileNotFoundError):
                            continue
                    if not script_launched:
                        print("No suitable terminal emulator found.")
                        print(f"Please manually run: {setup_script}")
                        print("Available terminal commands to try:")
                        print("  konsole --workdir . -e ./setup_linux.sh")
                        print("  gnome-terminal --working-directory . -- ./setup_linux.sh")
                        print("  xterm -e './setup_linux.sh'")
                        choice = input("\nHave you run the setup script manually? (y/n): ").lower()
                        if choice != 'y':
                            print("Please run the setup script before continuing.")
                            return
                except Exception as e:
                    print(f"Error launching setup script: {e}")
                    print(f"Please manually run: {setup_script}")
                break
        else:
            print("No OptiScaler setup script found - manual configuration may be needed")

    def configure_optiscaler_ini(self, install_dir: str):
        """
        Ensures OptiScaler.ini exists and sets Fsr4Update=true.
        """
        ini_path = Path(install_dir) / "OptiScaler.ini"
        print(f"Configuring OptiScaler.ini at: {ini_path}")
        if not ini_path.exists():
            print("Creating new OptiScaler.ini file")
            ini_content = """[OptiScaler]
Fsr4Update=true
Dx12Upscaler=auto
ColorResourceBarrier=auto
MotionVectorResourceBarrier=auto
OverrideNvapiDll=auto
"""
            with open(ini_path, 'w') as f:
                f.write(ini_content)
            print("Created OptiScaler.ini with Fsr4Update=true")
        else:
            print("OptiScaler.ini exists, updating Fsr4Update setting")
            with open(ini_path, 'r') as f:
                lines = f.readlines()
            fsr4_found = False
            for i, line in enumerate(lines):
                if line.strip().startswith('Fsr4Update='):
                    lines[i] = 'Fsr4Update=true\n'
                    fsr4_found = True
                    break
            if not fsr4_found:
                in_optiscaler_section = False
                for i, line in enumerate(lines):
                    if line.strip() == '[OptiScaler]':
                        in_optiscaler_section = True
                        continue
                    if in_optiscaler_section and (line.startswith('[') or i == len(lines) - 1):
                        insert_pos = i if line.startswith('[') else i + 1
                        lines.insert(insert_pos, 'Fsr4Update=true\n')
                        break
                else:
                    lines.append('\n[OptiScaler]\nFsr4Update=true\n')
            with open(ini_path, 'w') as f:
                f.writelines(lines)
        if ini_path.exists():
            with open(ini_path, 'r') as f:
                content = f.read()
                if 'Fsr4Update=true' in content:
                    print("✓ Confirmed: Fsr4Update=true is set in OptiScaler.ini")
                else:
                    print("⚠ Warning: Fsr4Update=true not found in OptiScaler.ini")
                    print("INI content preview:")
                    print(content[:500] + "..." if len(content) > 500 else content)

    def save_installation(self, install_info: Dict):
        installs = self.load_installations()
        installs.append(install_info)
        with open(self.installs_file, 'w') as f:
            import json
            json.dump(installs, f, indent=2)

    def load_installations(self) -> List[Dict]:
        if self.installs_file.exists():
            with open(self.installs_file, 'r') as f:
                import json
                return json.load(f)
        return []

    def uninstall_optiscaler(self, install_info: Dict) -> bool:
        """
        Uninstalls OptiScaler and restores any backup files.
        """
        install_path = Path(install_info["install_path"])
        self.run_optiscaler_removal_script(str(install_path))
        optiscaler_files = [
            "OptiScaler.dll", "OptiScaler.ini", "OptiScaler.log", "OptiScaler Setup.bat",
            "setup_linux.sh", "setup_windows.bat", "remove_optiscaler.sh",
            "dxgi.dll", "winmm.dll", "version.dll", "dbghelp.dll",
            "d3d12.dll", "wininet.dll", "winhttp.dll", "OptiScaler.asi",
            "nvngx.dll", "libxess.dll", "amd_fidelityfx_fsr2.dll",
            "amd_fidelityfx_fsr3.dll", "ffx_fsr2_api_x64.dll"
        ]
        optiscaler_dirs = [
            "D3D12_Optiscaler", "DlssOverrides", "Licenses"
        ]
        print("Cleaning up remaining OptiScaler files...")
        for filename in optiscaler_files:
            file_path = install_path / filename
            if file_path.exists():
                file_path.unlink()
                print(f"Removed: {filename}")
        for dirname in optiscaler_dirs:
            dir_path = install_path / dirname
            if dir_path.exists() and dir_path.is_dir():
                shutil.rmtree(dir_path)
                print(f"Removed directory: {dirname}")
        print("Restoring original game files...")
        for original_name, backup_path in install_info.get("backup_files", {}).items():
            backup_file = Path(backup_path)
            original_file = install_path / original_name
            if backup_file.exists():
                shutil.move(backup_file, original_file)
                print(f"Restored: {original_name}")
        # Remove FSR4 DLL from compatdata
        if install_info.get("fsr4_dll_copied", False):
            compatdata_path = self.steam_utils.get_compatdata_path(install_info["game"]["app_id"])
            if compatdata_path:
                self.fsr_manager.remove_fsr4_dll_from_compatdata(install_info["game"]["app_id"], compatdata_path)
        return True

    def run_optiscaler_removal_script(self, install_dir: str):
        """
        Tries to run a provided OptiScaler removal script.
        """
        install_path = Path(install_dir)
        removal_scripts = [
            install_path / "remove_optiscaler.sh",
            install_path / "uninstall_optiscaler.sh",
            install_path / "remove.sh",
            install_path / "uninstall.sh"
        ]
        for removal_script in removal_scripts:
            if removal_script.exists():
                try:
                    print(f"Found OptiScaler removal script: {removal_script.name}")
                    removal_script.chmod(0o755)
                    print("Opening interactive removal window...")
                    print("Please confirm removal options in the terminal window that opens.")
                    print(f"Running removal script in directory: {install_path}")
                    terminals = [
                        ["konsole", "--workdir", str(install_path), "-e", str(removal_script)],
                        ["gnome-terminal", "--working-directory", str(install_path), "--", str(removal_script)],
                        ["xfce4-terminal", "--working-directory", str(install_path), "-e", str(removal_script)],
                        ["alacritty", "--working-directory", str(install_path), "-e", str(removal_script)],
                        ["kitty", "--directory", str(install_path), str(removal_script)],
                        ["terminator", "--working-directory", str(install_path), "-e", str(removal_script)],
                        ["xterm", "-e", f"cd '{install_path}' && {removal_script}"]
                    ]
                    script_launched = False
                    for terminal_cmd in terminals:
                        try:
                            subprocess.run(["which", terminal_cmd[0]], capture_output=True, check=True)
                            subprocess.Popen(terminal_cmd)
                            print(f"Launched removal script in {terminal_cmd[0]}")
                            script_launched = True
                            input("\nPress Enter after you have completed the OptiScaler removal...")
                            break
                        except (subprocess.CalledProcessError, FileNotFoundError):
                            continue
                    if not script_launched:
                        print("No suitable terminal emulator found.")
                        print(f"Please manually run: {removal_script}")
                        print("Available terminal commands to try:")
                        print("  konsole --workdir . -e ./remove_optiscaler.sh")
                        print("  gnome-terminal --working-directory . -- ./remove_optiscaler.sh")
                        print("  xterm -e './remove_optiscaler.sh'")
                        choice = input("\nHave you run the removal script manually? (y/n): ").lower()
                        if choice != 'y':
                            print("Please run the removal script before continuing.")
                            return
                    print("OptiScaler removal script completed.")
                except Exception as e:
                    print(f"Error launching removal script: {e}")
                    print(f"Please manually run: {removal_script}")
                break
        else:
            print("No OptiScaler removal script found - proceeding with manual cleanup")