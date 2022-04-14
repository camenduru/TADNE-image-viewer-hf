#!/usr/bin/env python

from __future__ import annotations

import argparse
import functools
import io
import os
import pathlib
import tarfile

import gradio as gr
import numpy as np
import PIL.Image
from huggingface_hub import hf_hub_download

TITLE = 'TADNE (This Anime Does Not Exist) Image Viewer'
DESCRIPTION = '''The original TADNE site is https://thisanimedoesnotexist.ai/.

You can view images generated by the TADNE model with seed 0-99999.
The original images are 512x512 in size, but they are resized to 128x128 here.
'''
ARTICLE = None

TOKEN = os.environ['TOKEN']


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument('--theme', type=str)
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--share', action='store_true')
    parser.add_argument('--port', type=int)
    parser.add_argument('--disable-queue',
                        dest='enable_queue',
                        action='store_false')
    parser.add_argument('--allow-flagging', type=str, default='never')
    parser.add_argument('--allow-screenshot', action='store_true')
    return parser.parse_args()


def download_image_tarball(size: int, dirname: str) -> pathlib.Path:
    path = hf_hub_download('hysts/TADNE-sample-images',
                           f'{size}/{dirname}.tar',
                           repo_type='dataset',
                           use_auth_token=TOKEN)
    return path


def run(start_seed: int, nrows: int, ncols: int, image_size: int,
        min_seed: int, max_seed: int, dirname: str,
        tarball_path: pathlib.Path) -> np.ndarray:
    start_seed = int(start_seed)
    num = nrows * ncols
    images = []
    dummy = np.ones((image_size, image_size, 3), dtype=np.uint8) * 255
    with tarfile.TarFile(tarball_path) as tar_file:
        for seed in range(start_seed, start_seed + num):
            if not min_seed <= seed <= max_seed:
                images.append(dummy)
                continue
            member = tar_file.getmember(f'{dirname}/{seed:07d}.jpg')
            with tar_file.extractfile(member) as f:
                data = io.BytesIO(f.read())
            image = PIL.Image.open(data)
            image = np.asarray(image)
            images.append(image)
    res = np.asarray(images).reshape(nrows, ncols, image_size, image_size,
                                     3).transpose(0, 2, 1, 3, 4).reshape(
                                         nrows * image_size,
                                         ncols * image_size, 3)
    return res


def main():
    gr.close_all()

    args = parse_args()

    image_size = 128
    min_seed = 0
    max_seed = 99999
    dirname = '0-99999'
    tarball_path = download_image_tarball(image_size, dirname)

    func = functools.partial(run,
                             image_size=image_size,
                             min_seed=min_seed,
                             max_seed=max_seed,
                             dirname=dirname,
                             tarball_path=tarball_path)
    func = functools.update_wrapper(func, run)

    gr.Interface(
        func,
        [
            gr.inputs.Number(default=0, label='Start Seed'),
            gr.inputs.Slider(1, 10, step=1, default=2, label='Number of Rows'),
            gr.inputs.Slider(
                1, 10, step=1, default=5, label='Number of Columns'),
        ],
        gr.outputs.Image(type='numpy', label='Output'),
        title=TITLE,
        description=DESCRIPTION,
        article=ARTICLE,
        theme=args.theme,
        allow_screenshot=args.allow_screenshot,
        allow_flagging=args.allow_flagging,
        live=args.live,
    ).launch(
        enable_queue=args.enable_queue,
        server_port=args.port,
        share=args.share,
    )


if __name__ == '__main__':
    main()
