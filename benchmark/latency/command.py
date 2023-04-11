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
from pathlib import Path
from subprocess import call
from types_arg import SwitchSuffix

@click.command()
@click.option('-r', default=4, show_default=True, help='Radix of the switch')
@click.option('-d', default=8, show_default=True, help='Width of the data bus in bits')
@click.option('-f', default="newest", show_default=True, help='File name for benchmarking')
@click.argument('architecture', type=SwitchSuffix())
def latency(architecture:str, r:int, d: int, f:str):
    """
    Latency benchmarking.

    The suffix of the architecture to be tested must be specified: 'iq' for
    Inputed Queued switch and 'iq_voq' for Input Queued with Virtual Output Queues switch.
    
    The provision of the rest of parameters is encouraged.

    """

    # Prepare environment variables
    # checks:
    # if 'f' is  not a valid file name take the newest file as default
    dir_file = "traffic/profiles"

    try:
        files = os.listdir(dir_file)
        if f not in files:
            paths = [os.path.join(dir_file, basename) for basename in files]
            file_path = max(paths, key=os.path.getctime)
        else:
            file_path = f'{dir_file}/{f}'

        with open(file_path) as file:
            metadata = file.readline().strip('\n')
            metadata_list = metadata.split(",")    
            file.close()

        # if radix of the traffic profile does not match the radix of the experiment
        if(int(metadata_list[3]) == r):
            os.environ['BENCH_FILE'] = file_path
            os.environ['ARCHITECTURE'] = architecture
            os.environ['DATA_WIDTH'] = str(d)
            print(f'Selected traffic profile: {file_path}')
            print('Starting latency benchmark.')
            call(f'make clean SUFFIX={architecture} DATA_WIDTH={d} RADIX={r}', shell=True)
            call(f'make WAVES=1 SUFFIX={architecture} DATA_WIDTH={d} RADIX={r} MODULE={"bench_switch_latency"}', shell=True)
            # call(f'make WAVES=1 SUFFIX={architecture} DATA_WIDTH={d} RADIX={r} MODULE={"bench_switch_latency"}', shell=True)
            print('Finished latency benchmark.')
        else:
            print(f'Radix {r} does not match radix {metadata_list[3]} in {file_path} traffic profile')
    
    except FileNotFoundError:
        print("There is no traffic pattern file available.")