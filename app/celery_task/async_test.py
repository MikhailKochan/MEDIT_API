import asyncio
import os
import glob
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
import aiofiles
from aiohttp import ClientSession, TCPConnector, FormData

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


def list_maker(gen):
    lst = [i for i in gen]
    return lst


def list_spliter(lst):
    n = np.array_split(lst, len(lst) // 20)
    return n


def task_maker(height, width):
    gen = space_selector(height, width)
    n = list_spliter(list_maker(gen))
    for i in n:
        yield i


def read_region(file: Image, start_row: int, start_col: int):
    start = time.time()
    img = file.read_region((start_row, start_col), 0, CUT_IMAGE_SIZE)
    img = img.convert('BGR;24')
    print(f'read region time: {time.time() - start} s')
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
    # start = time.time()
    arr = np.asarray(image)
    # print(f'arr time: {time.time() - start} s')
    return arr


def convert_to_bytes(image: Image) -> np:
    image_content = BytesIO()
    image.seek(0)
    image.save(image_content, format='JPEG')
    image_content.seek(0)
    return image_content


async def async_image_process(img: Image, start_row: int, start_col: int, loop):
    with ThreadPoolExecutor() as thread_pool:
        return await loop.run_in_executor(thread_pool, partial(read_region, img, start_row, start_col))


async def async_image_save_process(img: Image, loop, filename, f_path):
    with ThreadPoolExecutor() as thread_pool:
        return await loop.run_in_executor(thread_pool, partial(save_image, img, filename, f_path))


async def async_convert_process(img: Image, loop):
    with ThreadPoolExecutor() as thread_pool:
        return await loop.run_in_executor(thread_pool, partial(convert_to_bytes, img))


async def async_open_image(f_path, loop):
    with ThreadPoolExecutor() as thread_pool:
        return await loop.run_in_executor(thread_pool, partial(openslide.OpenSlide, f_path))


async def async_main(session, start_row, start_col, image, loop, filename, f_path, number):
    url = 'http://localhost:8001/uploadfile/'
    try:
        image = await async_image_process(image, start_row, start_col, loop)
        start = time.time()
        """bytes block"""
        # file = await async_convert_process(image, loop)
        # print(f'convert time: {time.time() - start} s')
        """write read block"""
        path_save = await async_image_save_process(image, loop, filename, f_path)
        async with aiofiles.open(path_save, 'rb') as f:
            file = await f.read()
        print(f'write and read file time: {time.time() - start} s')

        data = FormData()
        data.add_field('file',
                       file,
                       filename=filename,
                       content_type='application/image')
        params = {"uploadType": "multipart/form-data"}
        with await session.post(url, data=data, params=params) as resp:
            if resp.status != 200:
                print(number, "--ERROR--")
                print(resp)
            else:
                print("RESPONSE:", resp)

    except Exception as ex:
        print("EXCEPTOIN IN async_main: ", ex)
        return
    finally:
        os.remove(path_save)


async def bulk_request():
    """Make requests concurrently"""
    loop = asyncio.get_running_loop()

    f_path = glob.glob(f'{Config.UPLOAD_FOLDER}/*.svs')
    if f_path:
        f_path = f_path[0]
        start = time.time()
        image = await async_open_image(f_path, loop)
        height, width = image.level_dimensions[0]
        print(f'openslide image open time: {time.time() - start} s')
        tasks = []
        number = 0
        connector = TCPConnector(force_close=True)
        async with ClientSession(connector=connector) as session:
            for start_row, start_col, file_name in space_selector(height, width):
                tasks.append(async_main(session, start_row, start_col, image, loop, file_name, f_path, number))
                number += 1
                if number % 10 == 0:
                    await asyncio.gather(*tasks)
                    print(f'task start time: {time.time() - start} s')
                    tasks = []
                    # await asyncio.sleep(5)
                    # break
            await asyncio.gather(*tasks)
            print(number)
    else:
        print("NOT FILE IN DIRECTORY")


if __name__ == "__main__":
    start_t = time.time()
    asyncio.run(bulk_request())
    print(f'Finish time: {time.time() - start_t} s')
