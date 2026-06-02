import psutil
from gi.repository import GLib
from fabric.core.service import Service, Property

class ProcessMonitorService(Service):
    _instance = None

    @classmethod
    def get_default(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @Property(list, "read-write")
    def processes(self) -> list:
        return self._processes

    @Property(list, "read-write")
    def cpu_percents(self) -> list:
        return self._cpu_percents

    @Property(bool, "read-write", default_value=False)
    def monitoring(self) -> bool:
        return self._monitoring

    def __init__(self):
        super().__init__()
        self._monitoring = False
        self._processes = []
        self._process_cache = {}
        self._cpu_percents = []
        self._timeout_id = None
        self._update_interval = 2000
        self._first_update = True
        self._cpu_count = psutil.cpu_count()

    def start_monitoring(self):
        if self._monitoring:
            return
        self._monitoring = True
        self._first_update = True

        psutil.cpu_percent(percpu=True)
        for proc in psutil.process_iter():
            try:
                proc.cpu_percent()
            except:
                pass

        GLib.timeout_add(200, self._start_regular_updates)
        self.notify("monitoring")

    def _start_regular_updates(self):
        self._update()
        self._timeout_id = GLib.timeout_add(self._update_interval, self._update)
        return False

    def stop_monitoring(self):
        if not self._monitoring:
            return

        self._monitoring = False
        if self._timeout_id:
            GLib.source_remove(self._timeout_id)
            self._timeout_id = None

        self._processes = []
        self._process_cache.clear()
        self._cpu_percents = []
        self._first_update = True

        self.notify("monitoring")
        self.notify("processes")
        self.notify("cpu-percents")

    def _update(self) -> bool:
        if not self._monitoring:
            return False

        cpu_percents = psutil.cpu_percent(percpu=True)
        if cpu_percents != self._cpu_percents:
            self._cpu_percents = cpu_percents
            self.notify("cpu-percents")

        current_pids = set()
        structure_changed = False

        for proc in psutil.process_iter(['pid', 'name']):
            try:
                pid = proc.info['pid']
                current_pids.add(pid)

                if pid not in self._process_cache:
                    proc_dict = {
                        'pid': pid,
                        'name': proc.info['name'] or 'Unknown',
                        'cpu_percent': 0.0,
                        'memory_mb': 0.0,
                    }
                    self._process_cache[pid] = {'dict': proc_dict, 'proc': proc}
                    proc.cpu_percent()
                    structure_changed = True
                else:
                    entry = self._process_cache[pid]
                    proc_obj = entry['proc']
                    proc_dict = entry['dict']

                    try:
                        cpu = proc_obj.cpu_percent()
                        cpu_lazy = cpu / self._cpu_count
                        mem = round(proc_obj.memory_info().rss / 1024 / 1024, 1)
                        old_cpu = proc_dict['cpu_percent']
                        proc_dict['cpu_percent'] = round(cpu_lazy, 1)
                        proc_dict['memory_mb'] = mem
                        if abs(old_cpu - cpu_lazy) > 1.0:
                            structure_changed = True
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        pids_to_remove = [pid for pid in self._process_cache if pid not in current_pids]
        if pids_to_remove:
            for pid in pids_to_remove:
                del self._process_cache[pid]
            structure_changed = True

        process_list = [entry['dict'] for entry in self._process_cache.values()]
        process_list.sort(key=lambda p: p['cpu_percent'], reverse=True)

        if len(process_list) != len(self._processes):
            structure_changed = True
        elif not structure_changed and not self._first_update:
            for i, proc in enumerate(process_list):
                if i >= len(self._processes) or proc['pid'] != self._processes[i]['pid']:
                    structure_changed = True
                    break

        self._processes = process_list
        self._first_update = False

        if structure_changed:
            self.notify("processes")

        return True

    def kill_process(self, pid: int):
        try:
            if pid in self._process_cache:
                self._process_cache[pid]['proc'].terminate()
        except:
            pass

    def force_refresh(self):
        if self._monitoring:
            self.notify("processes")