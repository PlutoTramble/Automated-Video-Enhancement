import os
import subprocess
import sys
import time


def ai_show_progress(process: subprocess.Popen,
              temp_dir_in: str,
              temp_dir_out: str,
              is_srmd: bool):
    # FIXME: while checking files, sometimes the 'handler' changes files around
    #  which crashes the program.
    while True:  # While process is running
        if process.poll() is not None:
            print("")
            break

        # Show progress
        num_of_files_in: int = len(os.listdir(temp_dir_in))
        num_of_files_out: int = len(os.listdir(temp_dir_out))
        files_out_needed: int = num_of_files_in * 2
        if is_srmd:
            percentage_completed = \
                "{:.2f}".format(num_of_files_out / num_of_files_in * 100)
        else:
            percentage_completed = \
                "{:.2f}".format(num_of_files_out / files_out_needed * 100)
        sys.stdout.write(f"\rFiles in input: {num_of_files_in} | " 
                         f"Files in output: {num_of_files_out} | " 
                         f"{percentage_completed} % Completed |")
        sys.stdout.flush()
        time.sleep(2)
