import sys
import getopt
import os
from shutil import rmtree
import subprocess

from src.handler import VulkanHandle
from src.media.Media import VideoMedia

current_dir = os.getcwd()


def getOpt(argv):
    options = {"input": "",
               "output": "",
               "temporary_directory_location": "",
               "is_input_a_file": True,
               "is_output_a_file": True,
               "target_fps": 60,
               "resolution_threshold": "720x480"
               }

    try:
        opts, args = getopt.getopt(argv, "hi:o:t:f:r:", \
                                   ["input-file/folder=", "output-file/folder=",
                                    "tmp-location=", "fps=", "resolution-threshold="])
    except getopt.getopt.GetoptError:
        print("main.py -i <input-file/folder> -o <output-file/folder>")
        sys.exit(2)

    for option, argument in opts:
        # Option help
        if option == '-h':
            print("\nmain.py -i <input-file/folder> -o <output-file/folder>\n")
            print("-h to show argument help")
            print("-t to indicate where you want to create " \
                  "your temporary directory (To reduce wear on your storage)")
            print("-f to target a specific framerate. " \
                  "Defaults at 60 and you can't go more than 180.")
            print("-r if the specified resolution is under " \
                  "what you wrote in this format : \"<number>x<number>\" " \
                  "it will double the resolution. Defaults at 720x480")
            sys.exit()

        # Argument for input
        elif option in ("-i", "--input-file/folder"):
            path = f"{current_dir}/{argument}"
            if argument[0] == "/":
                path = argument
            options["input"] = path

            if os.path.exists(path):
                if os.path.isdir(path):
                    options["is_input_a_file"] = False
            else:
                raise IOError("Either the file or directory does not exist for the input")

        # Argument for output
        elif option in ("-o", "--output-file/folder"):
            path = f"{current_dir}/{argument}"
            if argument[0] == "/":
                path = argument
            options["output"] = path

            if os.path.exists(path):  # if not, assume it will output a file
                if os.path.isfile(path):
                    print("The file already exist for the output argument.")
                    response = input("Do you wish to overwrite it? " \
                                     "\nIt will delete immediately. y/n ")
                    if response[0].lower() == 'y':
                        os.remove(path)
                    else:
                        print("Stoping program...")
                        sys.exit()
                else:
                    options["is_output_a_file"] = False

        # Argument for temporary directory location
        elif option in ("-t", "--tmp-location"):
            path = f"{current_dir}/{argument}"
            if argument[0] == "/":
                path = argument
            options["temporary_directory_location"] = path

            if os.path.exists(path):
                if os.path.isfile(path):
                    raise IOError("The path specified for " \
                                  "the temporary directory is a file.")
            else:
                raise IOError("The path specified for the " \
                              "temporary directory doesn't exist.")

        # Argument for frames per second
        elif option in ("-f", "--fps"):
            if int(argument) > 180:
                options["target_fps"] = 180
            else:
                options["target_fps"] = int(argument)

        # Nothing to do for the resolution threshold.

    # Assuring that it's logical
    if options['temporary_directory_location'] == "":
        options["temporary_directory_location"] = current_dir

    if options["is_input_a_file"] == False and \
            options["is_output_a_file"] == True:
        raise IOError("It's impossible to take a whole directory into a file.")

    return options


def make_temp_dir(tmp_dir: str):
    print(f"Making temporary directory in : {tmp_dir}")
    if os.path.exists(tmp_dir):
        rmtree(tmp_dir)

    os.mkdir(tmp_dir)
    os.mkdir(f"{tmp_dir}/in")
    os.mkdir(f"{tmp_dir}/out")
    os.mkdir(f"{tmp_dir}/vidin")
    os.mkdir(f"{tmp_dir}/vidout")


if __name__ == "__main__":
    options = getOpt(sys.argv[1:])
    tmp_directory: str = f'{options["temporary_directory_location"]}/ave-tmp'

    # Checking if the "AIs" folder and its content exists"
    if not os.path.exists(f"{current_dir}/AIs"):
        os.mkdir(f"{current_dir}/AIs")
        raise FileNotFoundError("The \"AIs\" directory didn't exist. "
                                "The program created it but you need "
                                "to put stuff in it. "
                                "Follow the instructions on the repository.")

    if not os.path.exists(f"{current_dir}/AIs/rife-ncnn-vulkan") or \
            not os.path.exists(f"{current_dir}/AIs/rife-v2.3") or \
            not os.path.exists(f"{current_dir}/AIs/ifrnet-ncnn-vulkan") or \
            not os.path.exists(f"{current_dir}/AIs/IFRNet_L_Vimeo90K") or \
            not os.path.exists(f"{current_dir}/AIs/srmd-ncnn-vulkan") or \
            not os.path.exists(f"{current_dir}/AIs/models-srmd"):
        raise FileNotFoundError("There are file(s) that are missing."
                                " Please go look where to put stuff in the repository.")

    # Checking if user have ffmpeg
    try:
        subprocess.call(["ffmpeg"], shell=False,
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError("You need to install ffmpeg before running this program."):
        sys.exit(2)

    # Where the handling happens
    if options["is_input_a_file"]:
        make_temp_dir(tmp_directory)
        video = VideoMedia(options["input"])
        VulkanHandle.handler(options, video)
        rmtree(tmp_directory)
        exit(0)

    videos_in_input = os.listdir(options["input"])
    videos_in_input.sort()
    for vid in videos_in_input:
        make_temp_dir(tmp_directory)
        video = VideoMedia(f'{options["input"]}/{vid}')
        VulkanHandle.handler(options, video)
        rmtree(tmp_directory)
