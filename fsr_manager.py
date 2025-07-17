import shutil
from pathlib import Path
from typing import Optional, Dict

class FSRManager:
    """
    Handles detection, selection, and management of FSR4 DLLs (amdxcffx64.dll).
    """

    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        self.fsr4_dll_path = self.find_fsr4_dll()

    def find_fsr4_dll(self) -> Optional[Path]:
        # Check config directory first (user's selected version)
        config_dll = self.config_dir / "amdxcffx64.dll"
        if config_dll.exists():
            return config_dll
        search_paths = [
            Path.cwd() / "amdxcffx64.dll",
            Path(__file__).parent / "amdxcffx64.dll",
            Path.home() / "Downloads" / "amdxcffx64.dll",
            Path("/usr/lib/amdxcffx64.dll"),
            Path("/usr/local/lib/amdxcffx64.dll"),
            Path.home() / "Documents" / "fsr4" / "FSR 4.0" / "FSR 4.0.1" / "amdxcffx64.dll",
        ]
        for path in search_paths:
            if path.exists():
                return path
        fsr_search_dirs = [
            Path.cwd() / "fsr4_dlls",
            Path(__file__).parent / "fsr4_dlls",
            Path.home() / "Documents" / "fsr4",
            Path.home() / "Downloads",
        ]
        for search_dir in fsr_search_dirs:
            if search_dir.exists():
                for fsr_dir in search_dir.rglob("*FSR*"):
                    if fsr_dir.is_dir():
                        dll_file = fsr_dir / "amdxcffx64.dll"
                        if dll_file.exists():
                            return dll_file
        return None

    def find_available_fsr4_versions(self) -> Dict[str, Path]:
        """
        Search for all available FSR4 DLL versions in common/bundled locations.
        """
        versions = {}
        fsr_search_dirs = [
            Path.cwd() / "fsr4_dlls",
            Path(__file__).parent / "fsr4_dlls",
            Path.home() / "Documents" / "fsr4",
            Path.home() / "Downloads",
        ]
        for search_dir in fsr_search_dirs:
            if not search_dir.exists():
                continue
            for version_dir in search_dir.iterdir():
                if version_dir.is_dir():
                    dll_file = version_dir / "amdxcffx64.dll"
                    if dll_file.exists():
                        version_name = version_dir.name
                        versions[version_name] = dll_file
            for dll_file in search_dir.glob("**/amdxcffx64*.dll"):
                if dll_file.exists():
                    parent_name = dll_file.parent.name
                    if "4.0" in parent_name or "FSR" in parent_name:
                        versions[parent_name] = dll_file
        return versions

    def select_fsr4_version(self) -> bool:
        """
        Allow user to select or add a FSR4 DLL version.
        """
        versions = self.find_available_fsr4_versions()
        if not versions:
            print("No FSR4 DLL versions found in bundled directories.")
            return self.download_fsr4_dll()
        print("\n=== Available FSR4 DLL Versions ===")
        version_list = list(versions.items())
        for i, (version_name, dll_path) in enumerate(version_list, 1):
            print(f"{i}. {version_name}\n   Path: {dll_path}")
        print(f"{len(version_list) + 1}. Browse for custom DLL")
        print(f"{len(version_list) + 2}. Cancel")
        try:
            choice = int(input(f"\nSelect FSR4 version (1-{len(version_list) + 2}): "))
            if 1 <= choice <= len(version_list):
                selected_version, selected_path = version_list[choice - 1]
                target_dll = self.config_dir / "amdxcffx64.dll"
                shutil.copy2(selected_path, target_dll)
                print(f"✓ Selected FSR4 version: {selected_version}")
                print(f"✓ Copied to: {target_dll}")
                self.fsr4_dll_path = target_dll
                return True
            elif choice == len(version_list) + 1:
                return self.download_fsr4_dll()
            else:
                print("Cancelled FSR4 version selection")
                return False
        except (ValueError, IndexError):
            print("Invalid selection")
            return False

    def download_fsr4_dll(self) -> bool:
        print("amdxcffx64.dll not found. This file is required for FSR4 functionality.")
        print("Please obtain amdxcffx64.dll from your system32 folder and place it in one of these locations:")
        print(f"1. Current directory: {Path.cwd()}")
        print(f"2. Script directory: {Path(__file__).parent}")
        print(f"3. Config directory: {self.config_dir}")
        print("\nYou can copy it from: C:\\Windows\\System32\\amdxcffx64.dll (on Windows)")
        print("Or from your Wine prefix system32 folder if you have it installed there.")
        choice = input("\nDo you want to specify a custom path to amdxcffx64.dll? (y/n): ").lower()
        if choice == 'y':
            custom_path = input("Enter full path to amdxcffx64.dll: ").strip()
            source_dll = Path(custom_path)
            if source_dll.exists():
                target_dll = self.config_dir / "amdxcffx64.dll"
                try:
                    shutil.copy2(source_dll, target_dll)
                    self.fsr4_dll_path = target_dll
                    print(f"Copied amdxcffx64.dll to {target_dll}")
                    return True
                except Exception as e:
                    print(f"Error copying DLL: {e}")
            else:
                print("File not found at specified path")
        return False

    def copy_fsr4_dll_to_compatdata(self, app_id: str, compatdata_path: Path) -> bool:
        """
        Copy the selected FSR4 DLL to the Wine/Proton compatdata system32 directory for a game.
        """
        if not self.fsr4_dll_path or not self.fsr4_dll_path.exists():
            print("FSR4 DLL not found. Please select a version...")
            if not self.select_fsr4_version():
                return False
        system32_path = compatdata_path / "pfx" / "drive_c" / "windows" / "system32"
        system32_path.mkdir(parents=True, exist_ok=True)
        target_dll = system32_path / "amdxcffx64.dll"
        try:
            shutil.copy2(self.fsr4_dll_path, target_dll)
            print(f"Copied amdxcffx64.dll to {target_dll}")
            return True
        except Exception as e:
            print(f"Error copying FSR4 DLL: {e}")
            return False

    def remove_fsr4_dll_from_compatdata(self, app_id: str, compatdata_path: Path) -> bool:
        """
        Remove the FSR4 DLL from the Wine/Proton compatdata system32 directory for a game.
        """
        system32_path = compatdata_path / "pfx" / "drive_c" / "windows" / "system32"
        target_dll = system32_path / "amdxcffx64.dll"
        try:
            if target_dll.exists():
                target_dll.unlink()
                print(f"Removed amdxcffx64.dll from {target_dll}")
            return True
        except Exception as e:
            print(f"Error removing FSR4 DLL: {e}")
            return False