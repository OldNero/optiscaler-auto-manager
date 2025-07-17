import os
import subprocess
import sys
from typing import Optional, Dict, List

class DependencyManager:
    """Manages automatic detection and installation of dependencies."""

    def __init__(self):
        self.package_managers = {
            'apt': ['apt', 'apt-get'],
            'pacman': ['pacman'],
            'dnf': ['dnf', 'yum'],
            'zypper': ['zypper'],
            'emerge': ['emerge'],
            'apk': ['apk'],
            'xbps': ['xbps-install'],
            'pkg': ['pkg'],
            'brew': ['brew']
        }
        self.detected_pm = None
        self.clipboard_apps = {
            'xclip': {
                'name': 'xclip',
                'description': 'Simple clipboard utility (most common)',
                'packages': {
                    'apt': 'xclip',
                    'pacman': 'xclip',
                    'dnf': 'xclip',
                    'zypper': 'xclip',
                    'emerge': 'x11-misc/xclip',
                    'apk': 'xclip',
                    'xbps': 'xclip',
                    'pkg': 'xclip'
                }
            },
            'xsel': {
                'name': 'xsel',
                'description': 'Alternative clipboard utility',
                'packages': {
                    'apt': 'xsel',
                    'pacman': 'xsel',
                    'dnf': 'xsel',
                    'zypper': 'xsel',
                    'emerge': 'x11-misc/xsel',
                    'apk': 'xsel',
                    'xbps': 'xsel',
                    'pkg': 'xsel'
                }
            },
            'wl-copy': {
                'name': 'wl-copy',
                'description': 'Wayland clipboard utility',
                'packages': {
                    'apt': 'wl-clipboard',
                    'pacman': 'wl-clipboard',
                    'dnf': 'wl-clipboard',
                    'zypper': 'wl-clipboard',
                    'emerge': 'gui-apps/wl-clipboard',
                    'apk': 'wl-clipboard',
                    'xbps': 'wl-clipboard',
                    'pkg': 'wl-clipboard'
                }
            }
        }

    def detect_package_manager(self) -> Optional[str]:
        """Detect the system's package manager."""
        if self.detected_pm:
            return self.detected_pm
        for pm_name, commands in self.package_managers.items():
            for cmd in commands:
                try:
                    result = subprocess.run(['which', cmd], capture_output=True, text=True)
                    if result.returncode == 0:
                        self.detected_pm = pm_name
                        return pm_name
                except Exception:
                    continue
        return None

    def detect_distro(self) -> str:
        """Detect Linux distribution."""
        try:
            with open('/etc/os-release', 'r') as f:
                content = f.read()
                if 'ID=' in content:
                    for line in content.split('\n'):
                        if line.startswith('ID='):
                            return line.split('=')[1].strip('"')
        except Exception:
            pass
        return "unknown"

    def is_wayland(self) -> bool:
        """Check if running on Wayland."""
        return os.environ.get('WAYLAND_DISPLAY') is not None

    def install_package(self, package_name: str, pm_name: str = None) -> bool:
        """Install a package using the system package manager."""
        if not pm_name:
            pm_name = self.detect_package_manager()
        if not pm_name:
            print("❌ No supported package manager found")
            return False
        print(f"🔧 Installing {package_name} using {pm_name}...")
        install_commands = {
            'apt': ['sudo', 'apt', 'install', '-y', package_name],
            'pacman': ['sudo', 'pacman', '-S', '--noconfirm', package_name],
            'dnf': ['sudo', 'dnf', 'install', '-y', package_name],
            'zypper': ['sudo', 'zypper', 'install', '-y', package_name],
            'emerge': ['sudo', 'emerge', package_name],
            'apk': ['sudo', 'apk', 'add', package_name],
            'xbps': ['sudo', 'xbps-install', '-y', package_name],
            'pkg': ['sudo', 'pkg', 'install', '-y', package_name],
            'brew': ['brew', 'install', package_name]
        }
        if pm_name not in install_commands:
            print(f"❌ Package manager {pm_name} not supported")
            return False
        try:
            result = subprocess.run(install_commands[pm_name], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ Successfully installed {package_name}")
                return True
            else:
                print(f"❌ Failed to install {package_name}: {result.stderr}")
                return False
        except Exception as e:
            print(f"❌ Error installing {package_name}: {e}")
            return False

    def check_python_module(self, module_name: str, pip_name: str = None) -> bool:
        """Check if a Python module is available and install if needed."""
        if not pip_name:
            pip_name = module_name
        try:
            __import__(module_name)
            return True
        except ImportError:
            print(f"❌ Missing Python module: {module_name}")
            pip_commands = ['pip3', 'pip', 'python3 -m pip', 'python -m pip']
            for pip_cmd in pip_commands:
                try:
                    check_cmd = pip_cmd.split()[0] if ' ' not in pip_cmd else pip_cmd.split()[-1]
                    result = subprocess.run(['which', check_cmd], capture_output=True)
                    if result.returncode != 0:
                        continue
                    print(f"🔧 Installing {pip_name} using {pip_cmd}...")
                    install_cmd = f"{pip_cmd} install --user {pip_name}".split()
                    result = subprocess.run(install_cmd, capture_output=True, text=True)
                    if result.returncode == 0:
                        print(f"✅ Successfully installed {pip_name}")
                        try:
                            __import__(module_name)
                            return True
                        except ImportError:
                            print("⚠️ Module installed but still not importable, may need to restart")
                            return False
                    else:
                        print(f"❌ Failed with {pip_cmd}: {result.stderr}")
                except Exception as e:
                    print(f"❌ Error with {pip_cmd}: {e}")
                    continue
            pm = self.detect_package_manager()
            if pm:
                python_packages = {
                    'requests': {
                        'apt': 'python3-requests',
                        'pacman': 'python-requests',
                        'dnf': 'python3-requests',
                        'zypper': 'python3-requests',
                        'emerge': 'dev-python/requests',
                        'apk': 'py3-requests',
                        'xbps': 'python3-requests'
                    }
                }
                if pip_name in python_packages and pm in python_packages[pip_name]:
                    package_name = python_packages[pip_name][pm]
                    return self.install_package(package_name, pm)
            return False

    def check_system_tool(self, tool_name: str, package_name: str = None, auto_install: bool = False) -> bool:
        """Check if a system tool is available and install if needed."""
        if not package_name:
            package_name = tool_name
        try:
            result = subprocess.run(['which', tool_name], capture_output=True, text=True)
            if result.returncode == 0:
                return True
        except Exception:
            pass
        print(f"❌ Missing system tool: {tool_name}")
        if auto_install:
            choice = 'y'
        else:
            choice = input(f"Install {tool_name}? (y/n): ").lower()
        if choice == 'y':
            pm = self.detect_package_manager()
            if pm:
                package_mappings = {
                    '7z': {
                        'apt': 'p7zip-full',
                        'pacman': 'p7zip',
                        'dnf': 'p7zip',
                        'zypper': 'p7zip',
                        'emerge': 'app-arch/p7zip',
                        'apk': 'p7zip',
                        'xbps': 'p7zip'
                    },
                    'git': {
                        'apt': 'git',
                        'pacman': 'git',
                        'dnf': 'git',
                        'zypper': 'git',
                        'emerge': 'dev-vcs/git',
                        'apk': 'git',
                        'xbps': 'git'
                    },
                    'wine': {
                        'apt': 'wine',
                        'pacman': 'wine',
                        'dnf': 'wine',
                        'zypper': 'wine',
                        'emerge': 'app-emulation/wine-vanilla',
                        'apk': 'wine',
                        'xbps': 'wine'
                    },
                    'curl': {
                        'apt': 'curl',
                        'pacman': 'curl',
                        'dnf': 'curl',
                        'zypper': 'curl',
                        'emerge': 'net-misc/curl',
                        'apk': 'curl',
                        'xbps': 'curl'
                    },
                    'wget': {
                        'apt': 'wget',
                        'pacman': 'wget',
                        'dnf': 'wget',
                        'zypper': 'wget',
                        'emerge': 'net-misc/wget',
                        'apk': 'wget',
                        'xbps': 'wget'
                    }
                }
                if tool_name in package_mappings and pm in package_mappings[tool_name]:
                    package_name = package_mappings[tool_name][pm]
                return self.install_package(package_name, pm)
        return False

    def setup_clipboard_app(self) -> bool:
        """Set up clipboard functionality by installing a clipboard app."""
        installed_apps = []
        for app_name, app_info in self.clipboard_apps.items():
            try:
                result = subprocess.run(['which', app_name], capture_output=True, text=True)
                if result.returncode == 0:
                    installed_apps.append(app_name)
            except Exception:
                pass
        if installed_apps:
            print(f"✅ Found clipboard app(s): {', '.join(installed_apps)}")
            return True
        print("❌ No clipboard application found")
        print("Clipboard functionality is needed for copying Steam launch commands")
        if self.is_wayland():
            print("🔍 Detected Wayland - recommending wl-copy")
            recommended = 'wl-copy'
        else:
            print("🔍 Detected X11 - recommending xclip")
            recommended = 'xclip'
        print("\nAvailable clipboard applications:")
        for i, (app_name, app_info) in enumerate(self.clipboard_apps.items(), 1):
            marker = " (recommended)" if app_name == recommended else ""
            print(f"{i}. {app_info['name']}: {app_info['description']}{marker}")
        print(f"{len(self.clipboard_apps) + 1}. Install all clipboard apps")
        print(f"{len(self.clipboard_apps) + 2}. Skip clipboard setup")
        try:
            choice = int(input(f"\nSelect clipboard app (1-{len(self.clipboard_apps) + 2}): "))
            if choice == len(self.clipboard_apps) + 2:
                print("⚠️ Skipping clipboard setup - launch commands won't be copied automatically")
                return False
            elif choice == len(self.clipboard_apps) + 1:
                pm = self.detect_package_manager()
                if not pm:
                    print("❌ No package manager detected")
                    return False
                success = True
                for app_name, app_info in self.clipboard_apps.items():
                    if pm in app_info['packages']:
                        package_name = app_info['packages'][pm]
                        if not self.install_package(package_name, pm):
                            success = False
                return success
            elif 1 <= choice <= len(self.clipboard_apps):
                app_name = list(self.clipboard_apps.keys())[choice - 1]
                app_info = self.clipboard_apps[app_name]
                pm = self.detect_package_manager()
                if not pm:
                    print("❌ No package manager detected")
                    return False
                if pm in app_info['packages']:
                    package_name = app_info['packages'][pm]
                    return self.install_package(package_name, pm)
                else:
                    print(f"❌ Package not available for {pm}")
                    return False
            else:
                print("❌ Invalid selection")
                return False
        except ValueError:
            print("❌ Invalid input")
            return False

    def check_all_dependencies(self) -> bool:
        """Check and install all required dependencies."""
        print("🔍 Checking dependencies...")
        pm = self.detect_package_manager()
        distro = self.detect_distro()
        is_wayland = self.is_wayland()
        print(f"📊 System Info:")
        print(f"   Distribution: {distro}")
        print(f"   Package Manager: {pm or 'Not detected'}")
        print(f"   Display Server: {'Wayland' if is_wayland else 'X11'}")
        all_ok = True
        print("\n🐍 Checking Python modules...")
        if not self.check_python_module('requests'):
            all_ok = False
        print("\n🔧 Checking system tools...")
        system_tools = {
            '7z': 'p7zip',
            'git': 'git',
            'wine': 'wine',
            'curl': 'curl',
            'wget': 'wget'
        }
        missing_tools = []
        for tool_name, package_name in system_tools.items():
            try:
                result = subprocess.run(['which', tool_name], capture_output=True, text=True)
                if result.returncode == 0:
                    print(f"✅ {tool_name} found")
                else:
                    missing_tools.append((tool_name, package_name))
                    print(f"❌ {tool_name} not found")
            except Exception:
                missing_tools.append((tool_name, package_name))
                print(f"❌ {tool_name} not found")
        if missing_tools:
            print(f"\n🔧 Found {len(missing_tools)} missing tools")
            choice = input("Install all missing tools automatically? (y/n): ").lower()
            if choice == 'y':
                for tool_name, package_name in missing_tools:
                    self.check_system_tool(tool_name, package_name, auto_install=True)
            else:
                print("⚠️ Some tools are missing - you can install them individually later")
        print("\n📋 Checking clipboard functionality...")
        if not self.setup_clipboard_app():
            print("⚠️ Clipboard functionality limited")
        print("\n💻 Checking terminal emulators...")
        terminal_found = False
        terminals = ['konsole', 'gnome-terminal', 'xfce4-terminal', 'alacritty', 'kitty', 'terminator', 'xterm']
        for terminal in terminals:
            try:
                result = subprocess.run(['which', terminal], capture_output=True, text=True)
                if result.returncode == 0:
                    terminal_found = True
                    print(f"✅ Found terminal: {terminal}")
                    break
            except Exception:
                pass
        if not terminal_found:
            print("⚠️ No common terminal emulator found - OptiScaler setup scripts may need manual execution")
        return all_ok