import asyncio
import os
from sys import platform

if platform == 'win32':
    os.add_dll_directory(os.getcwd() + '/app/static/dll/openslide-win64-20171122/bin')

import openslide
import time
from config import Config


def main():
    f_path = "D:/svs/Andreeva14.29Y_GCT_Mal.svs"
    start = time.time()
    file = openslide.OpenSlide(f_path)
    print(f'openslide time: {time.time() - start} s')
    height, width = file.level_dimensions[0]
    print(f'openslide height width: {time.time() - start} s')

    CUT_IMAGE_SIZE = Config._CUT_IMAGE_SIZE
    h_rest = height % CUT_IMAGE_SIZE[1]
    w_rest = width % CUT_IMAGE_SIZE[0]
    s_col = int(h_rest / 2)
    s_row = int(w_rest / 2)

    h_sum = int(height / CUT_IMAGE_SIZE[1])
    w_sum = int(width / CUT_IMAGE_SIZE[0])

    for i in range(0, w_sum):
        for j in range(0, h_sum):

            start_row = j * CUT_IMAGE_SIZE[0] + s_row
            start_col = i * CUT_IMAGE_SIZE[1] + s_col
            print(f'openslide after for1: {time.time() - start} s')
            img = file.read_region((start_row, start_col), 0, CUT_IMAGE_SIZE)
            print(f'openslide after for2: {time.time() - start} s')
            img = img.convert('RGB')
            print(f'openslide after for3: {time.time() - start} s')
            print(img)
            print(f'openslide after for: {time.time() - start} s')
            break
        break


if __name__ == "__main__":
    main()
