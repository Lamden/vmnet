from multiprocessing import Process
import traceback, os, cProfile, pkg_resources, json
from vprof import runner
from os import getenv as env
from os.path import join, exists

class PProc(Process):
    def run(self, name, profiling=''):
        testname = env('TEST_NAME', 'test')
        testid = env('TEST_ID', '')
        nodename = env('HOST_NAME', 'node')
        profdir = join('profiles', testname, testid, nodename)
        profpath = join(profdir, name)

        if not os.path.exists(profdir) and profiling:
            os.makedirs(profdir)
        if profiling == 'n':
            pr = cProfile.Profile()
            pr.enable()
            super().run()
            pr.create_stats()
            pr.dump_stats('{}.stats'.format(profpath))
        elif profiling in set('cmph'):
            run_stats = runner.run_profilers((super().run, [], {}), profiling)
            with open('{}.json'.format(profpath), 'w+') as f:
                run_stats['version'] = pkg_resources.get_distribution("vprof").version
                f.write(json.dumps(run_stats))
        else:
            super().run()
