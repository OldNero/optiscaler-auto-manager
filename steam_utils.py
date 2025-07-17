import subprocess
from pathlib import Path
from typing import List, Optional, Dict

class SteamUtils:
    """
    Utility functions for detecting Steam installation, libraries, and games.
    """

    def __init__(self):
        self.steam_path = self.find_steam_path()

    def find_steam_path(self) -> Optional[Path]:
        steam_paths = [
            Path.home() / ".steam" / "steam",
            Path.home() / ".local" / "share" / "Steam",
            Path("/usr/share/steam"),
            Path.home() / ".steam" / "root",
            Path.home() / "snap" / "steam" / "common" / ".steam" / "steam",
            Path("/var/lib/flatpak/app/com.valvesoftware.Steam/home/.steam/steam"),
            Path.home() / ".var" / "app" / "com.valvesoftware.Steam" / "home" / ".steam" / "steam",
        ]
        for path in steam_paths:
            if path.exists():
                print(f"Found Steam at: {path}")
                return path
        print("Steam installation not found in standard locations")
        return None

    def find_all_steam_libraries(self) -> List[Path]:
        """
        Find all Steam library folders across all drives including external and NTFS.
        """
        libraries = []
        if self.steam_path:
            libraries.append(self.steam_path)
            library_config = self.steam_path / "steamapps" / "libraryfolders.vdf"
            if library_config.exists():
                try:
                    with open(library_config, 'r', encoding='utf-8') as f:
                        content = f.read()
                    import re
                    path_matches = re.findall(r'"path"\s*"([^"]+)"', content)
                    for path_str in path_matches:
                        library_path = Path(path_str)
                        if library_path.exists() and library_path not in libraries:
                            libraries.append(library_path)
                            print(f"Found additional Steam library: {library_path}")
                except Exception as e:
                    print(f"Error reading libraryfolders.vdf: {e}")
        additional_libraries = self._scan_all_drives_for_steam()
        for lib in additional_libraries:
            if lib not in libraries:
                libraries.append(lib)
        return libraries

    def _scan_all_drives_for_steam(self) -> List[Path]:
        """
        Scan all mounted drives for Steam installations and libraries.
        """
        steam_libraries = []
        try:
            result = subprocess.run(['mount'], capture_output=True, text=True)
            mount_lines = result.stdout.split('\n')
            mount_points = []
            for line in mount_lines:
                parts = line.split()
                if len(parts) >= 3 and parts[1] == 'on':
                    mount_point = parts[2]
                    if (mount_point.startswith('/mnt/') or 
                        mount_point.startswith('/media/') or 
                        mount_point.startswith('/run/media/') or
                        mount_point == '/' or
                        mount_point.startswith('/home')):
                        mount_points.append(Path(mount_point))
            external_locations = [
                Path('/mnt'),
                Path('/media'),
                Path('/run/media'),
            ]
            for ext_path in external_locations:
                if ext_path.exists():
                    try:
                        for subdir in ext_path.iterdir():
                            if subdir.is_dir():
                                mount_points.append(subdir)
                                try:
                                    for user_dir in subdir.iterdir():
                                        if user_dir.is_dir():
                                            mount_points.append(user_dir)
                                except PermissionError:
                                    pass
                    except PermissionError:
                        pass
            for mount_point in mount_points:
                steam_dirs = self._find_steam_dirs_in_path(mount_point)
                steam_libraries.extend(steam_dirs)
        except Exception as e:
            print(f"Error scanning drives: {e}")
        return steam_libraries

    def _find_steam_dirs_in_path(self, search_path: Path) -> List[Path]:
        """
        Find Steam directories in a given path.
        """
        steam_dirs = []
        if not search_path.exists():
            return steam_dirs
        try:
            steam_patterns = [
                "Steam",
                "steam", 
                ".steam",
                ".local/share/Steam",
                "SteamLibrary",
                "Games/Steam",
                "Program Files/Steam",
                "Program Files (x86)/Steam",
            ]
            for pattern in steam_patterns:
                potential_steam = search_path / pattern
                if potential_steam.exists():
                    steamapps_path = potential_steam / "steamapps"
                    if steamapps_path.exists():
                        steam_dirs.append(potential_steam)
                        print(f"Found Steam library at: {potential_steam}")
            try:
                for item in search_path.iterdir():
                    if item.is_dir() and item.name.lower() in ['steamapps', 'steam']:
                        parent = item.parent
                        if parent not in steam_dirs:
                            if (item / "common").exists() or (parent / "steam.exe").exists():
                                steam_dirs.append(parent)
                                print(f"Found Steam directory via steamapps: {parent}")
            except (PermissionError, OSError):
                pass
        except (PermissionError, OSError):
            pass
        return steam_dirs

    def is_ntfs_drive(self, path: Path) -> bool:
        """
        Check if a path is on an NTFS filesystem.
        """
        try:
            result = subprocess.run(['stat', '-f', '-c', '%T', str(path)], 
                                  capture_output=True, text=True)
            return 'ntfs' in result.stdout.lower()
        except Exception:
            return False

    def safe_case_insensitive_glob(self, path: Path, pattern: str) -> List[Path]:
        """
        Perform case-insensitive glob for NTFS drives.
        """
        matches = []
        matches.extend(path.glob(pattern))
        if self.is_ntfs_drive(path):
            variations = [
                pattern.lower(),
                pattern.upper(),
                pattern.title(),
            ]
            for variation in variations:
                try:
                    matches.extend(path.glob(variation))
                except Exception:
                    pass
        return list(set(matches))

    def get_steam_games(self) -> List[Dict]:
        """
        List installed Steam games with basic info.
        """
        if not self.steam_path:
            print("Steam installation not found")
            return []
        games = []
        steam_libraries = self.find_all_steam_libraries()
        print(f"Scanning {len(steam_libraries)} Steam libraries for games...")
        for library_path in steam_libraries:
            steamapps_path = library_path / "steamapps"
            if not steamapps_path.exists():
                continue
            print(f"Scanning library: {library_path}")
            manifest_files = self.safe_case_insensitive_glob(steamapps_path, "appmanifest_*.acf")
            for manifest_file in manifest_files:
                try:
                    with open(manifest_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    app_id = None
                    name = None
                    install_dir = None
                    for line in content.split('\n'):
                        line = line.strip()
                        if line.startswith('"appid"'):
                            app_id = line.split('"')[3]
                        elif line.startswith('"name"'):
                            name = line.split('"')[3]
                        elif line.startswith('"installdir"'):
                            install_dir = line.split('"')[3]
                    if app_id and name and install_dir:
                        game_path = steamapps_path / "common" / install_dir
                        if game_path.exists():
                            existing_game = next((g for g in games if g["app_id"] == app_id), None)
                            if not existing_game:
                                games.append({
                                    "app_id": app_id,
                                    "name": name,
                                    "install_dir": install_dir,
                                    "path": str(game_path),
                                    "library_path": str(library_path)
                                })
                            else:
                                try:
                                    existing_mtime = Path(existing_game["path"]).stat().st_mtime
                                    current_mtime = game_path.stat().st_mtime
                                    if current_mtime > existing_mtime:
                                        for i, game in enumerate(games):
                                            if game["app_id"] == app_id:
                                                games[i] = {
                                                    "app_id": app_id,
                                                    "name": name,
                                                    "install_dir": install_dir,
                                                    "path": str(game_path),
                                                    "library_path": str(library_path)
                                                }
                                                break
                                except OSError:
                                    pass
                except Exception as e:
                    print(f"Error reading manifest {manifest_file}: {e}")
        print(f"Found {len(games)} games across all Steam libraries")
        return sorted(games, key=lambda x: x["name"])

    def find_game_executable_paths(self, game_path: str) -> List[Dict[str, str]]:
        """
        Find all possible executable locations for a given game.
        """
        game_dir = Path(game_path)
        exe_locations = []
        for exe_file in game_dir.rglob("*.exe"):
            if not exe_file.is_file():
                continue
            skip_paths = ["engine", "redist", "directx", "vcredist", "_commonredist", "tools", "crash"]
            skip_names = ["unins", "setup", "launcher", "redist", "vcredist", "directx", "crash"]
            path_str = str(exe_file.parent).lower()
            name_str = exe_file.name.lower()
            if (any(skip in path_str for skip in skip_paths) or 
                any(skip in name_str for skip in skip_names)):
                continue
            exe_type = "Other"
            priority = 3
            if exe_file.parent == game_dir:
                exe_type = "Main Game Directory"
                priority = 1
            elif "_shipping" in name_str:
                exe_type = "Shipping Executable (UE)"
                priority = 1
            elif any(folder in str(exe_file.parent).lower() for folder in ["bin/x64", "retail", "binaries/win64"]):
                exe_type = "Common Game Folder"
                priority = 2
            elif "ue4" in name_str or "ue5" in name_str:
                continue
            location_info = {
                "path": str(exe_file.parent),
                "exe_name": exe_file.name,
                "type": exe_type,
                "priority": priority,
                "relative_path": str(exe_file.parent.relative_to(game_dir))
            }
            existing = next((loc for loc in exe_locations if loc["path"] == location_info["path"]), None)
            if existing:
                if priority < existing["priority"]:
                    existing.update(location_info)
            else:
                exe_locations.append(location_info)
        exe_locations.sort(key=lambda x: (x["priority"], len(Path(x["path"]).parts), x["path"]))
        return exe_locations

    def get_compatdata_path(self, app_id: str) -> Optional[Path]:
        if not self.steam_path:
            return None
        compatdata_path = self.steam_path / "steamapps" / "compatdata" / app_id
        if compatdata_path.exists():
            return compatdata_path
        return None