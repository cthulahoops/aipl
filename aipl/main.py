from typing import List

import os
import sys

from .interpreter import AIPLInterpreter
from .table import LazyRow


def vd_singlestep(inputs:List[LazyRow], cmd):
    import visidata
    @visidata.VisiData.api
    def uberquit(vd):
        raise BaseException('user abort')

    inputs = list(r._asdict() for r in inputs)
    sheet = visidata.PyobjSheet('current_input', source=inputs)
    sheet.help = '{sheet.recentcmd}'
    argstr = ' '.join(str(x) for x in cmd.args)
    kwargstr = ' '.join(f'{k}={v}' for k, v in cmd.kwargs.items())
    sheet.recentcmd = f'[line {cmd.linenum}] !' + ' '.join([cmd.opname, argstr, kwargstr])
    sheet.addCommand('Q', 'quit-really', 'uberquit()')
    visidata.vd.run(sheet)


def main(*args):
    opts = []  # -x options
    scripts = []  # .aipl scripts to run
    kwargs = {}  # key=value parameters 

    for arg in args:
        if arg.startswith('-'):
            opts.append(arg)
        elif '=' in arg:
            k, v = arg.split('=', maxsplit=1)
            kwargs[k] = v
        else:
            scripts.append(arg)

    if not scripts:
        print('no script on stdin: nothing to do', file=sys.stderr)
        return

    aipl = AIPLInterpreter('aipl-cache.sqlite')

    # dup stdin/stdout if necessary

    if not sys.stdin.isatty():
        fin = open('/dev/tty')
        aipl.stdin = open(os.dup(0))
        os.dup2(fin.fileno(), 0)
        stdin_contents = aipl.stdin.read()
        fin.close()
    else:
        aipl.stdin = sys.stdin
        stdin_contents = ''

    if not sys.stdout.isatty():
        fout = open('/dev/tty', mode='w')
        aipl.stdout = open(os.dup(1))  # for dumping to stdout from interface
        os.dup2(fout.fileno(), 1)
        fout.close() # close file descriptors for original stdin/stdout
    else:
        aipl.stdout = sys.stdout

    # parse a few options
    if '-d' in opts:
        aipl.debug = True
        aipl.single_step = vd_singlestep

    if '-x' in opts:
        aipl.debug = True
        aipl.single_step = lambda *args, **kwargs: breakpoint()

    aipl.globals = kwargs

    for fn in scripts:
        aipl.run(open(fn).read(), stdin_contents)
