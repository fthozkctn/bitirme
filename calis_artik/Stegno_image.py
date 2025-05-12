from PIL import Image
import os.path
from os import path
import base64
from colorama import init
import os
import getpass
import sys
from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto import Random
import numpy as np
from scipy.fftpack import dct, idct

headerText = "M6nMjy5THr2J"

def encrypt(key, source, encode=True):
    key = SHA256.new(key).digest()
    IV = Random.new().read(AES.block_size)
    encryptor = AES.new(key, AES.MODE_CBC, IV)
    padding = AES.block_size - len(source) % AES.block_size
    source += bytes([padding]) * padding
    data = IV + encryptor.encrypt(source)
    return base64.b64encode(data).decode() if encode else data

def decrypt(key, source, decode=True):
    if decode:
        source = base64.b64decode(source.encode())
    key = SHA256.new(key).digest()
    IV = source[:AES.block_size]
    decryptor = AES.new(key, AES.MODE_CBC, IV)
    data = decryptor.decrypt(source[AES.block_size:])
    padding = data[-1]
    if data[-padding:] != bytes([padding]) * padding:
        raise ValueError("Invalid padding...")
    return data[:-padding]

def convertToRGB(img):
    try:
        rgba_image = img
        rgba_image.load()
        background = Image.new("RGB", rgba_image.size, (255, 255, 255))
        background.paste(rgba_image, mask=rgba_image.split()[3])
        print("Converted image to RGB ")
        return background
    except Exception as e:
        print("Couldn't convert image to RGB - %s" % e)

def getPixelCount(img):
    width, height = Image.open(img).size
    return width * height

def encodeImage(image, message, filename):
    try:
        # Convert image to YCbCr color space for DCT processing
        img_array = np.array(image.convert("YCbCr")).astype(float)
        height, width, _ = img_array.shape
        
        # Ensure image dimensions are divisible by 8
        height = height - height % 8
        width = width - width % 8
        img_array = img_array[:height, :width]
        
        # Convert message to binary
        binary_message = ''.join(format(ord(ch), '08b') for ch in message)
        binary_message += '1'  # Stop bit
        binary_message = binary_message.ljust(len(binary_message) + (8 - len(binary_message) % 8) % 8, '0')
        
        # Check if image can hold the message
        max_bits = (height // 8) * (width // 8)  # One bit per 8x8 block
        if len(binary_message) > max_bits:
            raise Exception("Message too long for image capacity")
        
        bit_index = 0
        # Process each 8x8 block
        for y in range(0, height, 8):
            for x in range(0, width, 8):
                if bit_index >= len(binary_message):
                    break
                # Apply DCT to Y channel (luminance)
                block = img_array[y:y+8, x:x+8, 0]
                dct_block = dct(dct(block.T, norm='ortho').T, norm='ortho')
                
                # Embed bit in a mid-frequency coefficient (e.g., (4,4))
                if bit_index < len(binary_message):
                    coeff = dct_block[4, 4]
                    # Modify coefficient to encode bit
                    bit = int(binary_message[bit_index])
                    coeff = abs(coeff) + 10 if bit == 1 else abs(coeff) - 10
                    dct_block[4, 4] = coeff
                    bit_index += 1
                
                # Inverse DCT
                img_array[y:y+8, x:x+8, 0] = idct(idct(dct_block.T, norm='ortho').T, norm='ortho')
        
        # Convert back to RGB and save
        img_array = np.clip(img_array, 0, 255).astype(np.uint8)
        encoded_image = Image.fromarray(img_array, mode='YCbCr').convert('RGB')
        encoded_filename = filename.split(".")[0] + "-enc.png"
        encoded_image.save(os.path.join("frame_folder", encoded_filename))
    except Exception as e:
        print("An error occurred - %s" % e)
        sys.exit(0)

def decodeImage(image):
    try:
        # Convert to YCbCr
        img_array = np.array(image.convert("YCbCr")).astype(float)
        height, width, _ = img_array.shape
        height = height - height % 8
        width = width - width % 8
        
        binary_message = ""
        # Process each 8x8 block
        for y in range(0, height, 8):
            for x in range(0, width, 8):
                block = img_array[y:y+8, x:x+8, 0]
                dct_block = dct(dct(block.T, norm='ortho').T, norm='ortho')
                coeff = dct_block[4, 4]
                # Extract bit based on coefficient modification
                bit = '1' if coeff > 0 else '0'
                binary_message += bit
        
        # Convert binary to text
        decoded = ""
        for i in range(0, len(binary_message) - 8, 8):
            byte = binary_message[i:i+8]
            if byte[0] == '1' and all(b == '0' for b in byte[1:]):  # Stop bit
                break
            ascii_value = int(byte, 2)
            decoded += chr(ascii_value)
        
        return decoded
    except Exception as e:
        print("An error occurred - %s" % e)
        sys.exit()

def main(op, password, img_path, message=""):
    if op == 1:
        img = img_path
        message = headerText + message
        if not path.exists(img):
            raise Exception("Image not found!")
        
        # Approximate capacity check (1 bit per 8x8 block)
        width, height = Image.open(img).size
        max_bits = (height // 8) * (width // 8)
        if len(message) * 8 > max_bits:
            raise Exception("Given message is too long to be encoded in the image.")
        
        cipher = ""
        if password != "":
            cipher = encrypt(key=password.encode(), source=message.encode())
            cipher = headerText + cipher
        else:
            cipher = headerText + message
        
        image = Image.open(img)
        if image.mode != "RGB":
            image = convertToRGB(image)
        newimg = image.copy()
        encodeImage(image=newimg, message=cipher, filename=img.split("\\").pop())
    
    elif op == 2:
        img = img_path
        if not path.exists(img):
            raise Exception("Image not found!")
        
        image = Image.open(img)
        cipher = decodeImage(image)
        header = cipher[:len(headerText)]
        if header.strip() != headerText:
            return "Invalid data!"
        
        decrypted = ""
        cipher = cipher[len(headerText):]
        
        if password != "":
            try:
                decrypted = decrypt(key=password.encode(), source=cipher)
                header = decrypted.decode()[:len(headerText)]
                if header != headerText:
                    print("Wrong password!")
                    sys.exit(0)
                decrypted = decrypted[len(headerText):]
                return decrypted.decode("utf-8")
            except Exception as e:
                print("Wrong password!")
                sys.exit(0)
        else:
            return cipher[len(headerText):]

if __name__ == "__main__":
    print("IMGHIDE allows you to hide texts inside an image using DCT. You can also protect these texts with a password using AES-256.")
    print()

    try:
        # Prompt user for operation
        op = int(input("Enter operation (1 for encode, 2 for decode): "))
        if op not in [1, 2]:
            raise ValueError("Operation must be 1 (encode) or 2 (decode)")

        # Prompt for image path
        img_path = input("Enter the path to the image (e.g., image.png): ").strip()
        
        # Prompt for password (optional)
        password = getpass.getpass("Enter password (leave blank for none): ").strip()

        # Prompt for message if encoding
        message = ""
        if op == 1:
            message = input("Enter the message to hide: ").strip()
        
        # Call main with user-provided arguments
        result = main(op, password, img_path, message)
        
        # If decoding, print the result
        if op == 2:
            print("Decoded message:", result)

    except ValueError as ve:
        print(f"Error: {ve}")
    except Exception as e:
        print(f"An error occurred: {e}")