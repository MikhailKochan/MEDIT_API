import asyncio
import os
import numpy as np
from sys import platform

if platform == 'win32':
    os.add_dll_directory(os.getcwd() + '/app/static/dll/openslide-win64-20171122/bin')

import openslide
import time
from config import Config

from PIL import Image
from functools import partial
from concurrent.futures import ThreadPoolExecutor
from aiohttp import ClientSession, FormData
import aiofiles
from io import BytesIO


CUT_IMAGE_SIZE = Config.__dict__['_CUT_IMAGE_SIZE']


def space_selector(height: int, width: int):
    # start = time.time()
    h_sum = int(height / CUT_IMAGE_SIZE[1])
    w_sum = int(width / CUT_IMAGE_SIZE[0])

    h_rest = height % CUT_IMAGE_SIZE[1]
    w_rest = width % CUT_IMAGE_SIZE[0]

    s_col = int(h_rest / 2)
    s_row = int(w_rest / 2)

    for i in range(0, w_sum):
        for j in range(0, h_sum):

            start_row = j * CUT_IMAGE_SIZE[0] + s_row
            start_col = i * CUT_IMAGE_SIZE[1] + s_col

            filename = f"im_.{str(i)}.{str(j)}"
            # print(f'generator time: {time.time() - start} s')
            yield start_row, start_col, filename


def main():
    # CUT_IMAGE_SIZE = Config.__dict__['_CUT_IMAGE_SIZE']
    print(CUT_IMAGE_SIZE)
    f_path = "D:/svs/Andreeva14.29Y_GCT_Mal.svs"
    start = time.time()
    file = openslide.OpenSlide(f_path)

    print(f'openslide time: {time.time() - start} s')
    height, width = file.level_dimensions[0]

    print(f'openslide height width: {time.time() - start} s')
    # gen = space_selector(height, width)
    for start_row, start_col, _ in space_selector(height, width):
        print(start_row, start_col)
    # [print(img.convert('RGB')) for img in gen]

    print(f'openslide after for1: {time.time() - start} s')
    # img = file.read_region((start_row, start_col), 0, CUT_IMAGE_SIZE)
    # print(f'openslide after for2: {time.time() - start} s')
    # print(f'openslide after for3: {time.time() - start} s')
    #
    # print(f'openslide after for: {time.time() - start} s')


# loop = asyncio.get_running_loop()
# thread_pool = concurrent.futures.ThreadPoolExecutor()


def read_region(file: Image, start_row: int, start_col: int):
    img = file.read_region((start_row, start_col), 0, CUT_IMAGE_SIZE)
    img = img.convert('RGB')
    return img


def save_image(image: Image, filename, f_path):
    img_filename = os.path.basename(f_path)
    save_folder = os.path.join(Config.CUTTING_FOLDER, img_filename)
    path_to_save = os.path.join(save_folder, f"{filename}.jpg")
    if not os.path.exists(save_folder):
        os.mkdir(save_folder)
    image.save(path_to_save)
    return path_to_save


def convert_to_np(image: Image) -> np:
    start = time.time()
    arr = np.asarray(image)
    print(f'arr time: {time.time() - start} s')
    return arr


async def async_image_process(img: Image, start_row: int, start_col: int, loop):
    with ThreadPoolExecutor() as thread_pool:
        return await loop.run_in_executor(thread_pool, partial(read_region, img, start_row, start_col))


async def async_image_save_process(img: Image, loop, filename, f_path):
    with ThreadPoolExecutor() as thread_pool:
        return await loop.run_in_executor(thread_pool, partial(save_image, img, filename, f_path))


async def async_convert_process(img: Image, loop):
    with ThreadPoolExecutor() as thread_pool:
        return await loop.run_in_executor(thread_pool, partial(convert_to_np, img))


async def async_open_image(f_path, loop):
    with ThreadPoolExecutor() as thread_pool:
        return await loop.run_in_executor(thread_pool, partial(openslide.OpenSlide, f_path))


async def async_main(session, start_row, start_col, file, loop, filename, f_path):
    url = 'http://localhost:8001/uploadfile'
    # data = FormData()
    try:
        start = time.time()
        image = await async_image_process(file, start_row, start_col, loop)
        print(f'main after read region time: {time.time() - start} s')

        start = time.time()
        path_save = await async_image_save_process(image, loop, filename, f_path)
        print(f'main after image_save time: {time.time() - start} s')
        async with aiofiles.open(path_save, 'rb') as f:
            start = time.time()
            fl = await f.read()
            # print(len(fl))
            data = {'file': fl, 'filename': f"{filename}"}
            resp = await session.post(url, data=data)

        print(f'main after post time: {time.time() - start} s')
    except Exception as ex:
        print("EXCEPTOIN IN async_main: ", ex)
        return
    if resp.status == 200:
        print(resp)
        os.remove(path_save)


async def bulk_request():
    """Make requests concurrently"""
    loop = asyncio.get_running_loop()
    f_path = "D:/svs/Andreeva14.29Y_GCT_Mal.svs"
    start = time.time()
    file = await async_open_image(f_path, loop)
    height, width = file.level_dimensions[0]
    print(f'openslide image open time: {time.time() - start} s')
    tasks = []
    # file_list = glob.glob("/home/nina_admin/fast_api/fastapi/save/ger_test/*.jpg")
    async with ClientSession() as session:
        for start_row, start_col, file_name in space_selector(height, width):
            tasks.append(async_main(session, start_row, start_col, file, loop, file_name, f_path))
            if len(tasks) >= 1:
                await asyncio.gather(*tasks)
                time.sleep(1)
                tasks = []
                break
        # time.sleep(1)
        # await asyncio.gather(*tasks)


if __name__ == "__main__":
    start_t = time.time()
    asyncio.run(bulk_request())
    print(f'Finish time: {time.time() - start_t} s')
