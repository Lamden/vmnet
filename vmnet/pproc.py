from multiprocessing import Process
import traceback, os, cProfile, pkg_resources, json
from vprof import runner

class PProc(Process):
    def run(self, name, profiling=''):
        testname = os.getenv('TEST_NAME', 'test')
        testid = os.getenv('TEST_ID', '')
        nodename = os.getenv('HOST_NAME', 'node')
        profdir = os.path.join('profiles', testname, testid, nodename)
        profpath = os.path.join(profdir, name)

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
