import argparse
import json
import logging
import os
import sys
import time
import threading

import config as parsed_config

from concurrent import futures
from logging.handlers import TimedRotatingFileHandler
from concurrent.futures import ThreadPoolExecutor, as_completed
from alert_threshold_metric_one import check1 as threshold_check



def setup_logging(log_file):
    rootLogger = logging.getLogger()
    rootLogger.setLevel(logging.INFO)

    fh = TimedRotatingFileHandler(log_file, when="midnight", interval=1, backupCount=10)
    sh = logging.StreamHandler(sys.stdout)

    formatter = logging.Formatter('%(asctime)s %(name)-12s [%(threadName)-12.12s] [%(levelname)-5.5s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    fh.setFormatter(formatter)
    formatter = logging.Formatter('%(asctime)s %(name)-12s: %(levelname)-5.5s %(message)s')
    sh.setFormatter(formatter)

    rootLogger.addHandler(fh)
    rootLogger.addHandler(sh)

    logger = logging.getLogger(__name__)
    logger.info("logger initialized")
    return logger


def read_parse_config(logger, config_file):
    configs = {}

    try:
        with open(config_file) as f:
            config_json = json.load(f)
    except:
        logger.error('invalid json detected in config')
        return False, None

    if config_json == None or 'configurations' not in config_json:
        logger.error('invalid configuration file')
        return False, None

    for config in config_json['configurations']:
        #print config
        if 'host' not in config and 'hostFile' not in config:
            logger.error('invalid config, host or hostFile not found')
            return False, None
        if 'metrics' not in config:
            logger.error('invalid config, metrics not found')
            return False, None
        if 'script' not in config:
            logger.error('invalid config, script not found')
            return False, None
        if 'value' not in config:
            logger.error('invalid config, value not found')
            return False, None
        if 'operator' not in config:
            logger.error('invalid config, operator not found')
            return False, None
        if 'threshold_operator' not in config:
            logger.error('invalid config, threshold_operator not found')
            return False, None
        if 'alert_value' not in config:
            logger.error('invalid config, alert_value not found')
            return False, None

        hosts = []
        if 'host' in config:
            hosts.append(config['host'])
        elif 'hostFile' in config:
            with open(config['hostFile']) as f:
                for line in f:
                    if line.startswith('#'):
                        continue
                    hosts.append(line.strip())

        for host in hosts:
            if config['enable'] != 'True':
                continue

            if config['exclude_hosts'] and host in config['exclude_hosts']:
                logger.info('excluding ' + host)
                continue

            c = parsed_config.Config(config['description'], config['enable'], config['script'], config['metrics'], config['exclude_hosts'], config['value'], config['operator'], config['threshold_operator'], config['alert_value'], config['alert_methods'])
            #c.add_metric(config['metric'])
            if host in configs:
                configs[host].append(c);
            else:
                configs[host] = [c]

    # TODO remove duplicate config
    #for config in configs:
    #    logger.info(config)

    #logger.info(configs)
    return True, configs


def start_check(logger, configs, arguments):
    logger.info('start checking ')

    # this one start one by one
    """
    executor = ThreadPoolExecutor(max_workers=50)
    for hostname,metrics in configs.items():
        logger.info(hostname)
        logger.info(metrics)
        #futures.append(executor.submit(task, logger, hostname, metrics))
        future = executor.submit(task, logger, hostname, metrics)
        #logger.info(future.done())
        #time.sleep(2)
        #print(future.done())
        #logger.info(future.result())
    executor.shutdown(wait=True)
    """

    # this start in mulitple of max 10 threads
    """
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(task, logger, hostname, metrics) for hostname,metrics in configs.items()]

    for future in as_completed(futures, timeout=1):
        logger.info(future.result(timeout=1))
    """

    # this one fire all , the timeout is the executor timeout
    with futures.ThreadPoolExecutor(max_workers=32) as ex:
        args = ((config, hostname, arguments, 120) for hostname, config in configs.items())
        results = ex.map(lambda p: threshold_check(*p), args, timeout=270)
        outputs = []
        try:
            for i in results:
                outputs.append(i)
        except futures._base.TimeoutError:
            logger.error('main thread timeout')
    logger.info(outputs)

def parse_argument():
    parser = argparse.ArgumentParser(description='app to alert if threshold is reached')

    # Required positional argument
    # parser.add_argument('pos_arg', type=int, help='A required integer positional argument')

    # Optional positional argument
    # parser.add_argument('opt_pos_arg', type=int, nargs='?', help='An optional integer positional argument')

    # Optional argument 
    parser.add_argument('--log_dir', help='log directory', default='log')
    parser.add_argument('--check_config_dir', help='directory that contains check configuration', default='conf')
    parser.add_argument('--state_file_dir', help='directory that contains state file', default='temp')

    # require argument
    parser.add_argument('--ssh_username', help='remote host ssh username', required=True)
    parser.add_argument('--ssh_port', help='remote host ssh port', required=True)
    parser.add_argument('--ssh_private_key', help='remote host user private key', required=True)
    parser.add_argument('--ssh_host_script_dir', help='remote host script directory', required=True)

    parser.add_argument('--alert_email_recipient', help='send the alert to this specify recipient email', required=True)
    parser.add_argument('--alert_email_from', help='sender email address', required=True)
    parser.add_argument('--alert_email_smtp_host', help='smtp hostname to send the alert to', required=True)
    parser.add_argument('--alert_email_smtp_port', help='smtp port', required=True)

    parser.add_argument('--alert_telegram_token', help='telegram token')
    parser.add_argument('--alert_telegram_api_key', help='telegram api key')
    parser.add_argument('--alert_telegram_chat_id', help='telegram chat id')

    # Switch
    #parser.add_argument('--switch', action='store_true', help='A boolean switch')

    return parser.parse_args()

def config_sanity_checks(args):
    if not os.path.exists(args.log_dir):
        os.makedirs(args.log_dir)

    if not os.path.exists(args.state_file_dir):
        os.makedirs(args.state_file_dir)

    if not os.path.isfile(args.check_config_dir + '/configurations.json'):
        sys.stderr.write('expected check config file {0} not exists \n'.format(args.check_config_dir + '/configurations.json'))
        return False

    return True


def main():
    args = parse_argument()

    if not config_sanity_checks(args):
        sys.exit(1)

    # setup logging
    logger = setup_logging(args.log_dir + '/alert_threshold.log')

    # read configuration file and then rearrange configuration object
    is_read_parse_config_ok, configs = read_parse_config(logger, args.check_config_dir + '/configurations.json')
    if not is_read_parse_config_ok:
        sys.exit(1)

    # start executor
    start_check(logger, configs, args)

if __name__ == "__main__":
    main()
