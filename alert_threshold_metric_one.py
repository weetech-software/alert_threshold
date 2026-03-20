
import datetime
import email.utils
import logging
import json
import operator
import os.path
import requests
import smtplib
import subprocess
import sys
import threading

from email.mime.text import MIMEText
from argparse import Namespace
from typing import Callable, TypeVar
import config as parsed_config


logger = logging.getLogger(__name__)


# subprocess with thread, so we have timeout and this work in python2 and python3
class Command(object):
    def __init__(self, cmd: str, res: list[bytes], arguments: Namespace):
        self.cmd = cmd
        self.res = res
        self.arguments = arguments
        self.process: subprocess.Popen[bytes] | None = None

    def run(self, timeout: float | None):
        def target(res: list[bytes]):
            self.process = subprocess.Popen(self.cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            stdout, stderr = self.process.communicate()
            res[0] = stdout
            if stderr:
                logger.error("error is %s", stderr)
                alert_root("mon script error", f"{stderr}\n{self.cmd}\n{stdout}", self.arguments)

        thread = threading.Thread(target=target, args=(self.res,))
        thread.start()

        thread.join(timeout=timeout)
        if thread.is_alive():
            if self.process is not None:
                self.process.terminate()
            thread.join()
        #print self.process.returncode


def update_state_file(stateFile: str, key: str, value: str) -> None:
    """
    update the stateFile based on the key and value specified

    :param stateFile: the state file where the key and value should be written to
    :param key: the key to write into the stateFile
    :param value: the value that belong to the key to write into the stateFile
    :returns: None

    """
    try:
        with open(stateFile, 'r', encoding='utf-8') as f:
            data = json.load(f)

        with open(stateFile, 'w', encoding='utf-8') as f:
            data[key] = value
            json.dump(data, f, indent=3, sort_keys=True)
            f.write("\n")
    except Exception:
        logger.exception(f"unable to read or write file {stateFile}")
        raise
        

def get_current_value(stateFile: str, key: str) -> int:
    """
    return the value associated with the key in the specified stateFile

    :param stateFile: the state file where the key and value present
    :param key: the key where the value is associated with
    :returns: 0 if there is not key found in the stateFile. else return the 
              value associated with the key
    :raises:
        JSONDecodeError: If file contains invalid JSON
        OSError: If file cannot be read
    """
    try:
        count = 0
        with open(stateFile, 'r', encoding='utf-8') as f:
            data = json.load(f)

            if key not in data:
                return count
            count = data[key]
        return count
    except (OSError, json.JSONDecodeError):
        logger.exception(f"unable to read file {stateFile}")
        raise


def create_state_file(stateFile: str, template: str='conf/pristine.json') -> None:
    """
    automatically create state file if it does not found in the directory temp/

    :param stateFile: the state file about to be create
    :param template: the template use to create stateFile. template file can be found at conf/pristine.json
    :returns: None

    """
    try:
        with open(template, 'r', encoding='utf-8') as f:
            data = json.load(f)

            with open(stateFile, 'w', encoding='utf-8') as sf:
                json.dump(data, sf, indent=3, sort_keys=True)
                sf.flush()
                sf.write("\n")
    except:
        logger.exception(f"unable to read file {template} or write file {stateFile}")
        raise

ops = {
    '<': operator.lt,
    '<=': operator.le,
    '==': operator.eq,
    '!=': operator.ne,
    '>=': operator.ge,
    '>': operator.gt
}

T = TypeVar('T')
def cmp(arg1: T, op: str, arg2: T) -> bool:
    operation: Callable[[T, T], bool] = ops.get(op)
    if operation is None:
        raise ValueError(f"Invalid operator: {op}. Must be one of {list(ops.keys())}")
    return operation(arg1, arg2)

def alert_root(email_subject: str, message: str, arguments: Namespace) -> None:
    msg = MIMEText(message, 'plain', 'utf-8')
    msg['To'] = email.utils.formataddr(('monitoring', arguments.alert_email_recipient))
    msg['From'] = email.utils.formataddr(('SMTPD', arguments.alert_email_from))
    msg['Subject'] = email_subject
    msg['Date'] = email.utils.formatdate()

    server = smtplib.SMTP(arguments.alert_email_smtp_host, arguments.alert_email_smtp_port)
    #server.set_debuglevel(True)
    try:
        server.sendmail(arguments.alert_email_from, [arguments.alert_email_recipient], msg.as_string())
    finally:
        server.quit()

def alert_email(email_subject: str, message: str, arguments: Namespace, recipients: list[str]):
    msg = MIMEText(message, 'plain', 'utf-8')
    msg['To'] = ', '.join(recipients)
    msg['From'] = email.utils.formataddr(('SMTPD', arguments.alert_email_from))
    msg['Subject'] = email_subject
    msg['Date'] = email.utils.formatdate()

    server = smtplib.SMTP(arguments.alert_email_smtp_host, arguments.alert_email_smtp_port)
    #server.set_debuglevel(True)
    try:
        server.sendmail(arguments.alert_email_from, recipients, msg.as_string())
    finally:
        server.quit()

def alert_telegram(subject: str, message: str, arguments: Namespace):
    payload = {'chat_id': arguments.alert_telegram_chat_id, 'text': subject + "\n\n" + message}
    url = f"https://api.telegram.org/{arguments.alert_telegram_token}:{arguments.alert_telegram_api_key}/sendMessage"
    requests.get(url, params=payload)

def alert(alert_configs: list[dict], subject: str, content: str, arguments: Namespace) -> None:
    for alert_config in alert_configs:
        if alert_config['type'] == 'email':
            alert_email(subject, content, arguments, alert_config['recipients'])
        if alert_config['type'] == 'telegram':
            alert_telegram(subject, content, arguments)

def check1(check_config: list[parsed_config.Config], ssh_host: str, arguments: Namespace, ops_timeout: int = 60) -> str:
    stateFile='{0}/{1}-alert-threshold.json'.format(arguments.state_file_dir, ssh_host.replace('.', '-'))

    if not os.path.isfile(stateFile):
        logger.warning(f"state file {stateFile} not exists, creating...")
        create_state_file(stateFile=stateFile, template='conf/pristine.json')

    try:
        result=[None]
        scripts=[]
        cmd = 'ssh -q -o StrictHostKeyChecking=no -p{0} -i {1} {2}@{3} "cd {4};'.format(arguments.ssh_port, arguments.ssh_private_key, arguments.ssh_username, ssh_host, arguments.ssh_host_script_dir)
        for config in check_config:
            cmd += f"./{config.script}; echo ''; "
            scripts.append(config.script)
        cmd += '"'
        command = Command(cmd=cmd, res=result, arguments=arguments)
        command.run(timeout=ops_timeout)
    except: 
        logger.error("Exception occurred during check execution", exc_info=True)

    results = result[0].decode('UTF-8').strip().split('\n')
    results = filter(None, results)
    script_results = dict(zip(scripts, results))

    for config in check_config:
        if config.script not in script_results:
            logger.error(f"expected script {config.script} not in script_results {script_results}")
            continue
        jsonString = '{{ {0} }}'.format(script_results[config.script])
        try:
            jsonObj = json.loads(jsonString)
        except:
            alert_root(email_subject="bad json string", message=jsonString, arguments=arguments)
            continue

        for metric in config.metrics:

            if metric not in jsonObj:
                logger.error(f"metric {metric} not found in {jsonString} ?!")
            try:
                current_value = float(jsonObj.get(metric, 0))
            except ValueError:
                logger.info(f"value error = {jsonObj.get(metric)}")
                current_value = 0

            # rename metric
            state_file_metric = '{0}.{1}'.format(config.script.replace('.', '_'), metric.replace('.', '_'));

            count_metric = float(get_current_value(stateFile=stateFile, key=state_file_metric))
            current_datetime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

            if cmp(arg1=current_value, op=config.operator, arg2=config.value):
                count_metric += 1
                update_state_file(stateFile=stateFile, key=state_file_metric, value=count_metric)
            else:
                update_state_file(stateFile=stateFile, key=state_file_metric, value=0)
        
            update_state_file(stateFile=stateFile, key='timestamp', value=current_datetime)

            # read again
            count_metric = int(get_current_value(stateFile=stateFile, key=state_file_metric))

            if cmp(arg1=count_metric, op=config.threshold_operator, arg2=config.alert_value):
                email_subject = f"alertThreshold - {ssh_host} - {metric}:{count_metric}/{config.alert_value}"
                email_content = 'host         : {0}\ndescription  : {6}\nmetric       : {1}\nscript       : {2}\nvalue        : {7}\ncurrent_value: {8}\ncount_metric : {3}\nalert_value  : {4}\ntimestamp    : {5}\n'.format(ssh_host, metric, config.script, count_metric, config.alert_value, current_datetime, config.description, config.value, current_value)
                alert_root(email_subject=email_subject, message=email_content, arguments=arguments)
                alert(alert_configs=config.alert_methods, subject=email_subject, content=email_content, arguments=arguments)
            else:
                pass

    return threading.current_thread().name + ": done"
