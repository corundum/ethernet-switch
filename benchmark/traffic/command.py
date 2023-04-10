"""

Copyright (c) 2023 Carlos Megías Núñez

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

"""

import click
import os
import random
import time

from pathlib import Path
from subprocess import call
from types_arg import TrafficType

@click.command()
@click.option('-r', default=4, show_default=True, help='Radix of the switch')
@click.option('-n', default=100, show_default=True, help='Number of frames to send per port')
@click.option('-l', default=64, show_default=True, help='Lower (exact) size limit of the payload in bytes')
@click.option('-u', default=1514, show_default=True, help='Upper size limit of the payload in bytes')
@click.argument('test', type=TrafficType())
def traffic(test:str, r:int, n: int, l: int, u:int):
    """
    Traffic generation.

    The type of the traffic to be generated must be specified:
    'custom' size for frames of equal 'l' size, 'min'imum size for frames of fixed 64 Bytes,
    'max'imum size for frames of fixed 1514 Bytes or 'uniform' for frames with sizes taken from a
    uniform distribution ['l', 'u'].

    The provision of the rest of parameters is encouraged.

    """
    print('Starting creating traffic profile.')
    # prepare benchmarking variables
    if test == "custom":
        frames_length = [l]*n
        frames_min = l
        frames_max = l
    elif test == "min":
        frames_length = [64]*n
        frames_min = 64
        frames_max = 64
    elif test == "max":
        frames_length = [1514]*n
        frames_min = 1514
        frames_max = 1514
    elif test == "uniform":
        frames_length = random.sample(range(l, u+1), n)
        frames_min = l
        frames_max = u

    # prepare output file
    dir_file = f'traffic/profiles'
    output_file = f'{dir_file}/{test}-{r}x{r}-{n}-({frames_min}-{frames_max}).txt' # consider adding {time.strftime("%Y%m%d-%H%M%S")}
    Path(dir_file).mkdir(parents=True, exist_ok=True)

    # check if configuration available
    try:
        Path(output_file).touch(exist_ok=False)
        f = open(output_file, "a")
        # metadata
        f.write(f'Test,{test},Radix,{r}\n')
        f.write(f'Input,Output,Length\n')

        # generate profile
        for input in range(r):
            # frames loop
            for length in frames_length:
                output = random.randrange(r)
                f.write(f'{input},{output},{length}\n')

        f.close()
        print('Finishing creating traffic profile.')

    except FileExistsError:
        print("Configuration already exists")
        return