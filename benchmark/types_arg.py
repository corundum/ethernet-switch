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

switch_suffixes = ['iq', 'iq_voq', 'oq']
traffic_types = ['custom', 'min', 'max', 'uniform']

class SwitchSuffix(click.ParamType):
    """A valid switch architecture suffix."""

    name = 'Switch suffix'

    def convert(self, value, param, ctx):
        if value in switch_suffixes:
            return(value)
        else:
            self.fail(f'{value!r} is not a valid switch architecture suffix.', param, ctx)

class TrafficType(click.ParamType):
    """A valid switch architecture suffix."""

    name = 'Latency test'

    def convert(self, value, param, ctx):
        if value in traffic_types:
            return(value)
        else:
            self.fail(f'{value!r} is not a valid latency test.', param, ctx)