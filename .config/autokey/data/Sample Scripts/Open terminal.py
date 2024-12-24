import subprocess
current_dir = os.getcwd()
subprocess.Popen(['gnome-terminal', '--working-directory', current_dir])