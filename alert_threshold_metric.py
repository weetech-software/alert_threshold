import argparse
import json
import logging
import os
import sys

from concurrent import futures
from logging.handlers import TimedRotatingFileHandler

from alert_threshold_metric_one import check1 as threshold_check
import config as parsed_config


def setup_logging(log_file: str) -> logging.Logger:
    rootLogger = logging.getLogger()
    rootLogger.setLevel(level=logging.INFO)

    fh = TimedRotatingFileHandler(filename=log_file, when="midnight", interval=1, backupCount=10)
    sh = logging.StreamHandler(stream=sys.stdout)

    formatter = logging.Formatter(fmt='%(asctime)s %(name)-12s [%(threadName)-12.12s] [%(levelname)-5.5s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    fh.setFormatter(fmt=formatter)
    formatter = logging.Formatter(fmt='%(asctime)s %(name)-12s: %(levelname)-5.5s %(message)s')
    sh.setFormatter(fmt=formatter)

    rootLogger.addHandler(hdlr=fh)
    rootLogger.addHandler(hdlr=sh)

    logger = logging.getLogger(name=__name__)
    logger.info(msg="logger initialized")
    return logger

def read_parse_config(
    logger: logging.Logger,
    config_file: str
) -> tuple[bool, dict[str, parsed_config.Config]]:
    configs = {}

    try:
        with open(file=config_file) as f:
            config_json = json.load(fp=f)
    except:
        logger.error(msg='invalid json detected in config')
        return False, None

    if config_json == None or 'configurations' not in config_json:
        logger.error(msg='invalid configuration file')
        return False, None

    for config in config_json['configurations']:
        #print config
        if 'host' not in config and 'hostFile' not in config:
            logger.error(msg='invalid config, host or hostFile not found')
            return False, None
        if 'metrics' not in config:
            logger.error(msg='invalid config, metrics not found')
            return False, None
        if 'script' not in config:
            logger.error(msg='invalid config, script not found')
            return False, None
        if 'value' not in config:
            logger.error(msg='invalid config, value not found')
            return False, None
        if 'operator' not in config:
            logger.error(msg='invalid config, operator not found')
            return False, None
        if 'threshold_operator' not in config:
            logger.error(msg='invalid config, threshold_operator not found')
            return False, None
        if 'alert_value' not in config:
            logger.error(msg='invalid config, alert_value not found')
            return False, None

        hosts = []
        if 'host' in config:
            hosts.append(config['host'])
        elif 'hostFile' in config:
            with open(file=config['hostFile']) as f:
                for line in f:
                    if line.startswith('#'):
                        continue
                    hosts.append(line.strip())

        for host in hosts:
            if config['enable'] != 'True':
                continue

            if config['exclude_hosts'] and host in config['exclude_hosts']:
                logger.info(msg='excluding ' + host)
                continue

            c = parsed_config.Config(
                description=config['description'],
                enable=config['enable'],
                script=config['script'],
                metrics=config['metrics'],
                exclude_hosts=config['exclude_hosts'] if config['exclude_hosts'] != "None" else [],
                value=config['value'],
                operator=config['operator'],
                threshold_operator=config['threshold_operator'],
                alert_value=config['alert_value'],
                alert_methods=config['alert_methods']
            )
            # if host exists in configs, append c to list, else create a new list with c as the first item
            configs.setdefault(host, []).append(c)

    # TODO remove duplicate config
    #for config in configs:
    #    logger.info(config)

    logger.info(msg=configs)
    return True, configs

def start_check(
    logger: logging.Logger,
    configs: dict[str, parsed_config.Config],
    arguments: argparse.Namespace
) -> None:
    logger.info(msg='start checking')

    # this one start one by one
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import time
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
    from concurrent.futures import ThreadPoolExecutor, as_completed
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(task, logger, hostname, metrics) for hostname,metrics in configs.items()]

    for future in as_completed(futures, timeout=1):
        logger.info(future.result(timeout=1))
    """

    # this one fire all , the timeout is the executor timeout
    with futures.ThreadPoolExecutor(max_workers=32) as ex:
        args = ({
            'check_config': config,
            'ssh_host': hostname,
            'arguments': arguments,
            'ops_timeout': 120
        } for hostname, config in configs.items())
        results = ex.map(lambda kwargs: threshold_check(**kwargs), args, timeout=270)
        outputs = []
        try:
            for i in results:
                outputs.append(i)
        except futures._base.TimeoutError:
            logger.error(msg='main thread timeout')
    logger.info(msg=outputs)

def parse_argument() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='app to alert if threshold is reached')

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

    return parser.parse_args()

def config_sanity_checks(args: argparse.Namespace) -> bool:
    if not os.path.exists(path=args.log_dir):
        os.makedirs(name=args.log_dir)

    if not os.path.exists(path=args.state_file_dir):
        os.makedirs(name=args.state_file_dir)

    config_file = args.check_config_dir + '/configurations.json'
    if not os.path.isfile(path=config_file):
        sys.stderr.write(
            f"expected check config file {config_file} not exists\n"
        )
        return False

    return True

def main() -> None:
    args = parse_argument()

    if not config_sanity_checks(args=args):
        sys.exit(status=1)

    # setup logging
    logger = setup_logging(log_file=f"{args.log_dir}/alert_threshold.log")

    # read configuration file and then rearrange configuration object
    is_read_parse_config_ok, configs = read_parse_config(
        logger=logger,
        config_file=f"{args.check_config_dir}/configurations.json"
    )
    if not is_read_parse_config_ok:
        sys.exit(status=1)

    # start executor
    start_check(logger=logger, configs=configs, arguments=args)

if __name__ == "__main__":
    main()
