import Stegno_image
import getpass
import cv2
import os
from subprocess import call, STDOUT
import shlex
from PIL import Image
import math
from colorama import init
from termcolor import cprint
from pyfiglet import figlet_format
from rich import print
from rich.console import Console
from rich.table import Table
import os
import getpass
from rich.progress import track
import numpy as np

temp_folder = "frame_folder"
console = Console()

def split_string(s_str, frame_width=1920, frame_height=1080):
    # Calculate max bits per frame based on DCT (1 bit per 8x8 block)
    blocks_per_frame = (frame_width // 8) * (frame_height // 8)
    max_bits = blocks_per_frame
    max_chars = max_bits // 8  # 8 bits per character
    if max_chars < 1:
        max_chars = 1  # Ensure at least one character per frame
    
    split_list = []
    for i in range(0, len(s_str), max_chars):
        split_list.append(s_str[i:i + max_chars])
    return split_list

def createTmp():
    if not os.path.exists(temp_folder):
        os.makedirs(temp_folder)

def countFrames(path):
    cap = cv2.VideoCapture(path)
    length = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    return length

def has_audio(path):
    # Check if video has an audio stream
    cmd = shlex.split(f"ffmpeg -i {path} -map 0:a -f null -")
    result = call(cmd, stdout=open(os.devnull, "w"), stderr=STDOUT, shell=True)
    return result == 0

def FrameCapture(path, op, password, message=""):
    createTmp()
    vidObj = cv2.VideoCapture(path)
    count = 0
    total_frame = countFrames(path)
    
    # Get frame dimensions for capacity calculation
    frame_width = int(vidObj.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(vidObj.get(cv2.CAP_PROP_FRAME_HEIGHT))
    split_string_list = split_string(message, frame_width, frame_height)
    position = 0
    outputMessage = ""
    
    while count < total_frame:
        success, image = vidObj.read()
        if not success:
            break
            
        frame_path = os.path.join(temp_folder, f"frame{count}.png")
        
        if op == 1:
            cv2.imwrite(frame_path, image)
            if position < len(split_string_list):
                print(
                    "Input in image working :- ",
                    split_string_list[position],
                )
                Stegno_image.main(
                    op,
                    password=password,
                    message=split_string_list[position],
                    img_path=frame_path,
                )
                position += 1
                os.remove(frame_path)

        if op == 2:
            str = Stegno_image.main(
                op,
                password=password,
                img_path=frame_path,
            )
            if str == "Invalid data!":
                break
            outputMessage = outputMessage + str

        count += 1

    if op == 1:
        print("[cyan]Please wait....[/cyan]")
        makeVideoFromFrame()
    
    if op == 2:
        print("[green]Message is :-\n[bold]%s[/bold][/green]" % outputMessage)

def makeVideoFromFrame():
    images = [img for img in os.listdir(temp_folder) if img.endswith(".png")]
    for img in images:
        if "-enc" in img:
            newImgName = img.split("-")[0] + ".png"
            os.rename(
                os.path.join(temp_folder, img),
                os.path.join(temp_folder, newImgName)
            )

    cmd = shlex.split(
        "ffmpeg -framerate 29.92 -i frame_folder/frame%01d.png -vcodec libx264 -pix_fmt yuv420p -crf 17 -preset fast output.mp4"
    )
    call(
        cmd,
        stdout=open(os.devnull, "w"),
        stderr=STDOUT,
        shell=True,
    )

def main():
    text = "Video"
    print("Choose one: ")
    print("[cyan]1. Encode[/cyan]\n[cyan]2. Decode[/cyan]")
    op = int(input(">> "))

    if op == 1:
        print(f"[cyan]{text} path (with extension): [/cyan]")
        img = input(">> ")

        print("[cyan]Message to be hidden: [/cyan]")
        message = input(">> ")
        password = ""

        print(
            "[cyan]Password to encrypt (leave empty if you want no password): [/cyan]"
        )
        password = getpass.getpass(">> ")

        if password != "":
            print("[cyan]Re-enter Password: [/cyan]")
            confirm_password = getpass.getpass(">> ")
            if password != confirm_password:
                print("[red]Passwords don't match try again [/red]")
                return

        # Check if video has audio
        audio_present = has_audio(img)
        if audio_present:
            cmd = shlex.split(f"ffmpeg -i {img} -q:a 0 -map a sample.mp3 -y")
            call(
                cmd,
                stdout=open(os.devnull, "w"),
                stderr=STDOUT,
                shell=True,
            )

        FrameCapture(img, op, password, message)

        if audio_present:
            cmd = shlex.split(
                f"ffmpeg -i output.mp4 -i sample.mp3 -c:v copy -c:a aac -shortest -y final.mp4"
            )
            call(
                cmd,
                stdout=open(os.devnull, "w"),
                stderr=STDOUT,
                shell=True,
            )
            if os.path.exists("sample.mp3"):
                os.remove("sample.mp3")
        else:
            cmd = shlex.split(
                f"ffmpeg -i output.mp4 -c:v copy -an -y final.mp4"
            )
            call(
                cmd,
                stdout=open(os.devnull, "w"),
                stderr=STDOUT,
                shell=True,
            )

        if os.path.exists("output.mp4"):
            os.remove("output.mp4")

    elif op == 2:
        print(f"[cyan]{text} path (with extension):[/cyan] ")
        img = input(">>")

        print("[cyan]Enter password (leave empty if no password):[/cyan] ")
        password = getpass.getpass(">>")
        FrameCapture(img, op, password)

if __name__ == "__main__":
    os.system("cls" if os.name == "nt" else "clear")
   
    print()
    print(
        "[bold]VIDEOHIDE[/bold] allows you to hide texts inside a video using DCT. You can also protect these texts with a password using AES-256."
    )
    print()
    main()