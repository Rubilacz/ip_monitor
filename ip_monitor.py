# -*- coding: utf-8 -*-

import urllib.request
import re
import argparse
import time

from config_store import ConfigStore
from mail_manager import Mail, MailManager

from apscheduler.schedulers.blocking import BlockingScheduler

def _get_current_time():
    return time.strftime('%Y-%m-%d %H:%M', time.localtime(time.time()))

class CmdExecutor:

    def __init__(self, config_store, mail_manager):
        self._config_store = config_store
        self._mail_manager = mail_manager
        self._parser = argparse.ArgumentParser()
        self._init_parse(self._parser)

    def _init_parse(self, parser):
        cmd_type = parser.add_mutually_exclusive_group()
        cmd_type.add_argument('-r', action='store_true')
        cmd_type.add_argument('-c', action='store_true')
        parser.add_argument('--ip', action='store_true')
        parser.add_argument('--config', action='store_true')
        parser.add_argument('-d')

    def submit(self, cmd, **kwargs):
        args = self._parser.parse_args(cmd.split(' '))
        if args.r and args.d:
            if args.ip:
                subject = self._config_store.get('command', 'ip_addr_subject')\
                    .format(response_time=_get_current_time())
                message = self._config_store.get('command', 'ip_addr_message')\
                    .format(ip_addr=self._config_store.get('ip_monitor', 'initial_ip'),\
                        promoter=kwargs['sender'])
                self._mail_manager.send(Mail(subject, message, args.d))
            elif args.config:
                pass


class Task:

    def __init__(self, uid, interval):
        self.uid = uid
        self.interval = interval

    def execute(self):
        pass


class CmdMonitorTask(Task):

    def __init__(self, config_store, mail_manager, cmd_executor):
        Task.__init__(self, CmdMonitorTask.__name__,\
            config_store.get_as_int('cmd_monitor', 'interval', 10))
        self._config_store = config_store
        self._mail_manager = mail_manager
        self._cmd_executor = cmd_executor

    def execute(self):
        while True:
            mail = self._mail_manager.pop(self._config_store.get('cmd_monitor', 'sender_matcher'),\
                self._config_store.get('cmd_monitor', 'subject_matcher'))
            print(mail)
            if not mail:
                break
            self._cmd_executor.submit(mail.message, sender=mail.sender)


class IpMonitorTask(Task):

    def __init__(self, config_store, mail_manager):
        Task.__init__(self, IpMonitorTask.__name__,\
            config_store.get_as_int('ip_monitor', 'interval', 10))
        self._current_ip = config_store.get('ip_monitor', 'initial_ip')
        self._config_store = config_store
        self._mail_manager = mail_manager

    def execute(self):
        ip = self._get_local_host_ip()
        if ip != self._current_ip:
            message = self._config_store.get('ip_monitor', 'ip_changed_message')\
                .format(previous=self._current_ip, present=ip)
            self._mail_manager.send(Mail(self._config_store.get('ip_monitor', 'ip_changed_subject'),\
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
        self._mail_manager = MailManager(imap_host=self._config_store.get('sys_email', 'imap_host'),\
            smtp_host=self._config_store.get('sys_email', 'smtp_host'))
        self._cmd_executor = CmdExecutor(self._config_store, self._mail_manager)
        self._scheduler = BlockingScheduler()
        self._ip_monitor_task = IpMonitorTask(self._config_store, self._mail_manager)
        self._cmd_monitor_task = CmdMonitorTask(self._config_store, self._mail_manager, self._cmd_executor)

    def start(self):
        self._mail_manager.authorize(self._config_store.get('sys_email', 'user'),\
                self._config_store.get('sys_email', 'password'))
        self._scheduler.add_job(self._ip_monitor_task.execute, 'interval',\
            minutes=self._ip_monitor_task.interval)
        self._scheduler.add_job(self._cmd_monitor_task.execute, 'interval',\
        minutes=self._cmd_monitor_task.interval)
        self._scheduler.start()

    def stop(self):
        self._scheduler.shutdown()
        self._mail_manager.revoke_auth()


if __name__ == '__main__':
    ip_monitor = IpMonitor('config.ini')
    try:
        ip_monitor.start()
    except KeyboardInterrupt:
        ip_monitor.stop()
        print('stop ip monitoring.')
