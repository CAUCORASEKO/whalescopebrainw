#!/usr/bin/env python3
# whalescope.py

import sys
import subprocess
import json
import argparse
import os
import logging
from appdirs import user_log_dir

# Logging
log_dir = user_log_dir("WhaleScope", "Cauco")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "whalescope.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

def get_python_command():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    # Preferir venv si existe
    venv_python = os.path.join(base_dir, 'venv', 'bin', 'python3')
    if os.path.exists(venv_python):
        return venv_python
    # Si no hay venv → usar Python actual del sistema
    return sys.executable

def get_site_packages_dir(base_dir):
    # Solo mirar dentro del venv
    venv_site_packages = os.path.join(base_dir, 'venv', 'lib', 'python3.11', 'site-packages')
    if os.path.exists(venv_site_packages):
        return venv_site_packages
    return None

def update_data(mode, start_date=None, end_date=None):
    logger = logging.getLogger(__name__)
    logger.info(f"Starting data update for mode '{mode}'")

    base_dir = os.path.dirname(os.path.abspath(__file__))

    scripts = {
        'bitcoin': os.path.join(base_dir, 'bitcoin.py'),
        'eth': os.path.join(base_dir, 'eth.py'),
        'binance_polar': os.path.join(base_dir, 'binance_polar.py'),
        'news-analytic': os.path.join(base_dir, 'staking_analysis.py')
    }

    output_files = {
        'bitcoin': os.path.join(base_dir, 'bitcoin_output.json'),
        'eth': os.path.join(base_dir, 'eth_output.json'),
        'binance_polar': os.path.join(base_dir, 'binance_polar_output.json'),
        'news-analytic': os.path.join(base_dir, 'news_analytic_output.json')
    }

    script = scripts.get(mode)
    output_file = output_files.get(mode)

    if not script or not os.path.exists(script):
        logger.error(f"Script '{script}' not found for mode '{mode}'")
        return {"error": f"Script '{script}' not found"}

    python_command = get_python_command()
    cmd = [python_command, script]

    if mode in ['bitcoin', 'eth']:
        if start_date and end_date:
            cmd.extend(['--start-date', start_date, '--end-date', end_date])
        else:
            logger.error(f"Fechas requeridas para {mode}")
            return {"error": f"Fechas requeridas para {mode}"}
    elif mode == 'news-analytic':
        # staking_analysis.py no requiere fechas
        cmd.append("--api")
    elif mode == 'binance_polar':
        cmd.append('binance_polar')

    env = {**os.environ, "PYTHONUNBUFFERED": "1"}
    site_packages_dir = get_site_packages_dir(base_dir)
    if site_packages_dir:
        env["PYTHONPATH"] = f"{site_packages_dir}{os.pathsep}{os.environ.get('PYTHONPATH', '')}"

    logger.info(f"Python command: {python_command}")
    logger.info(f"Executing: {' '.join(cmd)}")
    logger.info(f"PYTHONPATH: {env.get('PYTHONPATH', 'Not set')}")
    logger.info(f"Working directory: {base_dir}")

    try:
        version_result = subprocess.run([python_command, "--version"], capture_output=True, text=True)
        logger.info(f"Python version: {version_result.stdout.strip()}")
    except Exception as e:
        logger.error(f"Error checking Python version: {str(e)}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            cwd=base_dir
        )
        stdout_clean = result.stdout.strip()
        if result.returncode != 0:
            logger.error(f"Script failed with return code {result.returncode}, stderr: {result.stderr}, stdout: {stdout_clean}")
            return {"error": f"Script execution failed with code {result.returncode}: {result.stderr}"}
        if not stdout_clean:
            logger.error(f"Empty stdout, stderr: {result.stderr}")
            return {"error": f"Empty output from script, stderr: {result.stderr}"}

        data = json.loads(stdout_clean)

        # Validaciones por modo
        if mode in ['bitcoin', 'eth']:
            required_keys = ['markets', 'yields', 'top_flows', 'inflows', 'outflows',
                             'net_flow', 'price_history', 'fees', 'analysis', 'conclusion']
            if not all(k in data for k in required_keys):
                logger.error(f"Missing keys in {mode} data")
                return {"error": f"Invalid JSON structure from {mode}"}
        elif mode == 'binance_polar':
            if not isinstance(data, dict) or "results" not in data:
                logger.error("Binance Polar data must be a dict with 'results'")
                return {"error": "Invalid JSON structure from binance_polar"}
        elif mode == 'news-analytic':
            if not isinstance(data, dict) or "staking" not in data or "alerts" not in data:
                logger.error("Missing keys in news-analytic data")
                return {"error": "Invalid JSON structure from news-analytic"}

        with open(output_file, 'w') as f:
            json.dump(data, f, indent=4)

        logger.info(f"Data saved to {output_file}")
        return data
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {str(e)}, Output was: {result.stdout}")
        return {"error": f"Invalid JSON output: {str(e)}"}
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}, stderr: {result.stderr if 'result' in locals() else 'N/A'}")
        return {"error": f"Unexpected error: {str(e)}"}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WhaleScope data updater")
    parser.add_argument('mode', choices=['bitcoin', 'eth', 'binance_polar', 'news-analytic', 'all'], help="Mode to run")
    parser.add_argument('--start-date', type=str, help="Start date (YYYY-MM-DD)")
    parser.add_argument('--end-date', type=str, help="End date (YYYY-MM-DD)")
    args = parser.parse_args()

    modes = ['bitcoin', 'eth', 'binance_polar', 'news-analytic'] if args.mode == 'all' else [args.mode]
    results = {}

    for mode in modes:
        results[mode] = update_data(mode, args.start_date, args.end_date)

    print(json.dumps(results[args.mode] if args.mode != 'all' else results, indent=4))
    sys.stdout.flush()