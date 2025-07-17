import sys
from pathlib import Path

from dependency_manager import DependencyManager
from steam_utils import SteamUtils
from fsr_manager import FSRManager
from optiscaler_installer import OptiScalerInstaller

def main_menu():
    print("=" * 60)
    print("🚀 OptiScaler Manager - Enhanced Version")
    print("=" * 60)

    # Setup config dir
    config_dir = Path.home() / ".config" / "optiscaler_manager"
    config_dir.mkdir(parents=True, exist_ok=True)

    # Initialize managers
    dep_manager = DependencyManager()
    steam_utils = SteamUtils()
    fsr_manager = FSRManager(config_dir)
    installer = OptiScalerInstaller(config_dir, fsr_manager, steam_utils)

    # Startup dependency check
    print("\n🔍 Running startup dependency check...")
    if not dep_manager.check_python_module('requests'):
        print("❌ Critical dependency missing - exiting")
        sys.exit(1)

    # Quick check for common tools
    missing_tools = []
    tools_to_check = ['7z', 'git', 'wine']
    for tool in tools_to_check:
        try:
            import shutil
            if shutil.which(tool) is None:
                missing_tools.append(tool)
        except Exception:
            missing_tools.append(tool)
    if missing_tools:
        print(f"⚠️ Optional tools not found: {', '.join(missing_tools)}")
        print("   Use menu option 9 to install missing dependencies")
    else:
        print("✅ All common tools found")
    print("\n" + "=" * 60)

    while True:
        print("\n=== OptiScaler Manager ===")
        print("1. List Steam games")
        print("2. Install OptiScaler")
        print("3. View installations")
        print("4. Uninstall OptiScaler")
        print("5. Download latest nightly")
        print("6. Manage FSR4 DLL")
        print("7. Check/Install dependencies")
        print("8. Exit")

        choice = input("\nEnter choice (1-8): ").strip()

        if choice == "1":
            games = steam_utils.get_steam_games()
            for i, game in enumerate(games, 1):
                library_info = f" [Library: {game.get('library_path', 'Unknown')}]" if 'library_path' in game else ""
                print(f"{i}. {game['name']} (ID: {game['app_id']}){library_info}")

        elif choice == "2":
            games = steam_utils.get_steam_games()
            if not games:
                print("No Steam games found")
                continue
            print("\nSelect a game:")
            for i, game in enumerate(games, 1):
                print(f"{i}. {game['name']}")
            try:
                game_idx = int(input("Game number: ")) - 1
                selected_game = games[game_idx]
                print(f"\nAnalyzing game directory: {selected_game['name']}")
                print("Searching for executable locations...")
                exe_locations = steam_utils.find_game_executable_paths(selected_game["path"])
                if not exe_locations:
                    print("No suitable executable locations found")
                    print("This game may not be compatible or may have an unusual directory structure")
                    continue
                print(f"\nFound {len(exe_locations)} possible installation location(s):")
                print("=" * 80)
                for i, location in enumerate(exe_locations, 1):
                    print(f"{i}. {location['type']}")
                    print(f"   Executable: {location['exe_name']}")
                    print(f"   Path: {location['relative_path'] if location['relative_path'] != '.' else 'Game Root Directory'}")
                    print(f"   Full Path: {location['path']}")
                    print()
                print("Choose the installation location:")
                print("- Main Game Directory is usually the best choice")
                print("- Shipping Executable locations work well for UE games")
                print("- Choose based on where the main game .exe file is located")
                path_idx = int(input(f"\nInstallation location (1-{len(exe_locations)}): ")) - 1
                selected_location = exe_locations[path_idx]
                print(f"\nSelected: {selected_location['type']}")
                print(f"Installing to: {selected_location['path']}")
                zip_path = installer.download_latest_nightly()
                if not zip_path:
                    continue
                if installer.install_optiscaler(selected_game, selected_location, zip_path):
                    print("\n✓ OptiScaler installed successfully!")
                    print(f"Installation directory: {selected_location['path']}")
                    print("\nNext steps:")
                    print("1. The setup_linux.sh script should have been executed")
                    print("2. Configure launch options in Steam for the game")
                    print("3. Launch the game and press INSERT to open OptiScaler overlay")
                else:
                    print("✗ Installation failed")
            except (ValueError, IndexError):
                print("Invalid selection")

        elif choice == "3":
            installs = installer.load_installations()
            if not installs:
                print("No installations found")
                continue
            print("\nCurrent OptiScaler Installations:")
            print("=" * 60)
            for i, install in enumerate(installs, 1):
                print(f"{i}. {install['game']['name']}")
                print(f"   Installed: {install['timestamp']}")
                print(f"   Path: {install['install_path']}")
                if 'exe_location' in install:
                    exe_loc = install['exe_location']
                    print(f"   Type: {exe_loc['type']}")
                    print(f"   Executable: {exe_loc['exe_name']}")
                fsr4_status = "✓ FSR4 DLL copied" if install.get('fsr4_dll_copied', False) else "✗ FSR4 DLL not copied"
                print(f"   FSR4: {fsr4_status}")
                print()

        elif choice == "4":
            installs = installer.load_installations()
            if not installs:
                print("No installations to uninstall")
                continue
            print("\nSelect installation to uninstall:")
            print("=" * 60)
            for i, install in enumerate(installs, 1):
                print(f"{i}. {install['game']['name']}")
                print(f"   Installed: {install['timestamp']}")
                print(f"   Path: {install['install_path']}")
                if 'exe_location' in install:
                    exe_loc = install['exe_location']
                    print(f"   Type: {exe_loc['type']}")
                    print(f"   Executable: {exe_loc['exe_name']}")
                print()
            try:
                install_idx = int(input(f"Installation to uninstall (1-{len(installs)}): ")) - 1
                selected_install = installs[install_idx]
                print(f"\nUninstalling OptiScaler from: {selected_install['game']['name']}")
                print(f"Directory: {selected_install['install_path']}")
                confirmation = input("Are you sure you want to uninstall? (y/n): ").lower()
                if confirmation != 'y':
                    print("Uninstall cancelled")
                    continue
                if installer.uninstall_optiscaler(selected_install):
                    installs.pop(install_idx)
                    with open(installer.installs_file, 'w') as f:
                        import json
                        json.dump(installs, f, indent=2)
                    print("✓ OptiScaler uninstalled successfully!")
                else:
                    print("✗ Uninstallation failed")
            except (ValueError, IndexError):
                print("Invalid selection")

        elif choice == "5":
            zip_path = installer.download_latest_nightly()
            if zip_path:
                print(f"Downloaded to: {zip_path}")

        elif choice == "6":
            print("\n=== FSR4 DLL Management ===")
            if fsr_manager.fsr4_dll_path and fsr_manager.fsr4_dll_path.exists():
                print(f"Current FSR4 DLL: {fsr_manager.fsr4_dll_path}")
                current_dll = fsr_manager.fsr4_dll_path
                version_info = "Unknown"
                if "4.0.1" in str(current_dll):
                    version_info = "FSR 4.0.1"
                elif "4.0" in str(current_dll):
                    version_info = "FSR 4.0"
                print(f"Detected version: {version_info}")
                print("\n1. Change FSR4 DLL version")
                print("2. View available versions")
                print("3. Use current version")
                sub_choice = input("Enter choice (1-3): ").strip()
                if sub_choice == "1":
                    fsr_manager.select_fsr4_version()
                elif sub_choice == "2":
                    versions = fsr_manager.find_available_fsr4_versions()
                    if versions:
                        print("\nAvailable FSR4 versions:")
                        for name, path in versions.items():
                            print(f"- {name}: {path}")
                    else:
                        print("No bundled FSR4 versions found")
                elif sub_choice == "3":
                    print("Continuing with current FSR4 DLL")
            else:
                print("No FSR4 DLL found")
                print("\n1. Select from available versions")
                print("2. Browse for custom DLL")
                sub_choice = input("Enter choice (1-2): ").strip()
                if sub_choice == "1":
                    fsr_manager.select_fsr4_version()
                elif sub_choice == "2":
                    fsr_manager.download_fsr4_dll()

        elif choice == "7":
            print("\n=== Dependency Check and Installation ===")
            dep_manager.check_all_dependencies()
            input("\nPress Enter to continue...")

        elif choice == "8":
            break

        else:
            print("Invalid choice")