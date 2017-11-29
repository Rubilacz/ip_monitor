# -*- coding: utf-8 -*-

import urllib.request
import re

from config_store import ConfigStore
from mail_manager import Mail, MailManager

from apscheduler.schedulers.blocking import BlockingScheduler

class Task:

    def __init__(self, uid, interval):
        self.uid = uid
        self.interval = interval

    def execute(self):
        pass


class IpMonitorTask(Task):

    def __init__(self, config_store):
        Task.__init__(self, IpMonitorTask.__name__,\
            config_store.get_as_int('ip_monitor', 'interval', 5))
        self._current_ip = config_store.get('ip_monitor', 'initial_ip')
        self._config_store = config_store

    def execute(self):
        ip = self._get_local_host_ip()
        if ip != self._current_ip:
            manager = MailManager(smtp_host=self._config_store.get('sys_email',\
                'smtp_host'))
            manager.authorize(self._config_store.get('sys_email', 'user'),\
                self._config_store.get('sys_email', 'password'))
            message = self._config_store.get('ip_monitor', 'ip_changed_message')\
                .format(self._current_ip, ip)
            manager.send(Mail(self._config_store.get('ip_monitor', 'ip_changed_subject'),\
                message, self._config_store.get('admin_email', 'user')))
            self._config_store.set('ip_monitor', 'initial_ip', ip)
            self._current_ip = ip

    def _send_ip_request(self, web_url):
        with urllib.request.urlopen(web_url) as f:
            return f.read()

    def _re_search(self, regexp, content):
        return re.search(regexp, content).group(1)

    def _get_local_host_ip(self):
        raw_content = self._send_ip_request(self._config_store.get('ip_monitor', 'web_url'))
        content = raw_content.decode(self._re_search(\
            self._config_store.get('ip_monitor', 'charset_matcher'), str(raw_content)))
        return self._re_search(self._config_store.get('ip_monitor', 'ip_addr_matcher'), content)



class IpMonitor:

    def __init__(self, config_file):
        self._config_store = ConfigStore(config_file)
        self._scheduler = BlockingScheduler()
        self._ip_monitor_task = IpMonitorTask(self._config_store)

    def start(self):
        self._scheduler.add_job(self._ip_monitor_task.execute, 'interval',\
            minutes=self._ip_monitor_task.interval)
        self._scheduler.start()

    def stop(self):
        self._scheduler.shutdown()


if __name__ == '__main__':
    ip_monitor = IpMonitor('config.ini')
    try:
        ip_monitor.start()
    except KeyboardInterrupt:
        ip_monitor.stop()
        print('stop ip monitoring.')
