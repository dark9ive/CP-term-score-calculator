import os
import re
import json
import getpass
import requests
import argparse
import logging
import csv
import sys
from requests.utils import dict_from_cookiejar, cookiejar_from_dict
from urllib.parse import urlparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
site = os.getenv("SITE")  # Base URL of your OnlineJudge instance, set in .env
if not site:
    raise RuntimeError("Please set SITE in your .env file")

# Configuration
default_cookie_file = os.path.join(os.path.dirname(__file__), ".oj_api_cookies.json")  # store cookies in project directory
VERBOSE = False
PAGE_LIMIT = 250  # max records per API call


def configure_logging():
    """Configure logging for verbose mode."""
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s')
    for logger_name in ('requests', 'urllib3'):
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG)


def load_cookies(session, path=default_cookie_file):
    if VERBOSE:
        logging.debug(f"Loading cookies from {path}")
    if os.path.exists(path):
        try:
            data = json.load(open(path, 'r', encoding='utf-8'))
            jar = cookiejar_from_dict(data)
            session.cookies = jar
            if VERBOSE:
                logging.debug(f"Loaded cookies: {data}")
            return True
        except Exception as e:
            if VERBOSE:
                logging.debug(f"Failed to load cookies: {e}")
    return False


def save_cookies(session, path=default_cookie_file):
    data = dict_from_cookiejar(session.cookies)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f)
    os.chmod(path, 0o600)
    if VERBOSE:
        logging.debug(f"Saved cookies to {path}: {data}")


def clear_cookies_file(path=default_cookie_file):
    try:
        os.remove(path)
        if VERBOSE:
            logging.debug(f"Deleted cookie file: {path}")
    except FileNotFoundError:
        pass


def set_csrf_header(session):
    # choose csrf token matching site domain if multiple
    csrf_cookies = [c for c in session.cookies if c.name == 'csrftoken']
    if not csrf_cookies:
        raise RuntimeError("No csrftoken cookie found in session")
    site_domain = urlparse(site).hostname
    token_cookie = next((c for c in csrf_cookies if c.domain == site_domain), csrf_cookies[-1])
    session.headers.update({'X-CSRFToken': token_cookie.value})
    if VERBOSE:
        logging.debug(f"X-CSRFToken set to {token_cookie.value} (domain: {token_cookie.domain})")


def prompt_credentials():
    username = input("Username: ")
    password = getpass.getpass("Password: ")
    return username, password


def check_tfa_required(session, username):
    url = f"{site}/api/tfa_required"
    resp = session.post(url, json={"username": username})
    resp.raise_for_status()
    data = resp.json()
    return data.get('error') is None and data.get('data', {}).get('result', False)


def do_login(session, username, password, tfa_code=None):
    """Perform login with optional 2FA code and save session cookies on success."""
    url = f"{site}/api/login"
    payload = {"username": username, "password": password}
    if tfa_code:
        payload['tfa_code'] = tfa_code
    if VERBOSE:
        logging.debug(f"POST {url} with payload={payload}")
    resp = session.post(url, json=payload)
    resp.raise_for_status()
    data = resp.json()
    success = (data.get('error') is None and data.get('data') == 'Succeeded')
    if success:
        save_cookies(session)
    return success


def do_logout(session):
    url = f"{site}/api/logout"
    resp = session.post(url)
    resp.raise_for_status()
    session.cookies.set('sessionid', '', domain=urlparse(site).hostname, path='/')
    save_cookies(session)
    clear_cookies_file()
    print("Logged out successfully.")


def list_contests(session, rule_type):
    url = f"{site}/api/contests?offset=0&limit=100&keyword=&rule_type={rule_type}&status="
    resp = session.get(url)
    resp.raise_for_status()
    data = resp.json().get('data', {})
    results = data.get('results', [])
    print("Available contests:", file=sys.stderr)
    for c in results:
        print(f"  - {c['id']}: {c['title']}", file=sys.stderr)
    return [c['id'] for c in results]


def fetch_all_ranks(session, contest_id):
    url = f"{site}/api/contest_rank?offset=0&limit={PAGE_LIMIT}&contest_id={contest_id}"
    resp = session.get(url)
    resp.raise_for_status()
    data = resp.json().get('data', {})
    total = data.get('total', len(data.get('results', [])))
    results = data.get('results', [])
    for offset in range(PAGE_LIMIT, total, PAGE_LIMIT):
        url = f"{site}/api/contest_rank?offset={offset}&limit={PAGE_LIMIT}&contest_id={contest_id}"
        r = session.get(url)
        r.raise_for_status()
        results.extend(r.json().get('data', {}).get('results', []))
    return results


def results_to_csv_acm(results):
    # ACM scoring: first AC=full, second half, else 0
    qids = sorted({int(q) for e in results for q in e.get('submission_info', {})}, key=int)
    full = 100 / len(qids) if qids else 0
    writer = csv.writer(sys.stdout)
    header = ['username'] + [f"Q{idx+1}({qid})" for idx,qid in enumerate(qids)] + ['total']
    writer.writerow(header)
    for e in results:
        uname = e['user']['username']
        row = [uname]
        total_score = 0
        info = e.get('submission_info', {})
        for qid in qids:
            qi = info.get(str(qid), {})
            if qi.get('is_ac'):
                atts = qi.get('error_number',0)+1
                sc = full if atts==1 else (full/2 if atts==2 else 0)
            else:
                sc = 0
            row.append(f"{sc:.2f}")
            total_score += sc
        row.append(f"{total_score:.2f}")
        writer.writerow(row)


def results_to_csv_oi(results):
    # OI scoring: direct points
    qids = sorted({int(q) for e in results for q in e.get('submission_info', {})}, key=int)
    writer = csv.writer(sys.stdout)
    header = ['username'] + [f"Q{idx+1}({qid})" for idx,qid in enumerate(qids)] + ['total_score']
    writer.writerow(header)
    for e in results:
        uname = e['user']['username']
        row = [uname]
        info = e.get('submission_info', {})
        for qid in qids:
            sc = info.get(str(qid), 0)
            row.append(str(sc))
        row.append(str(e.get('total_score', sum(info.values()))))
        writer.writerow(row)


def main():
    parser = argparse.ArgumentParser(description="OnlineJudge API Tool")
    parser.add_argument('-v','--verbose',action='store_true')
    parser.add_argument('--logout',action='store_true')
    parser.add_argument('-m','--mode',type=str,help='ACM or OI')
    args = parser.parse_args()
    global VERBOSE
    VERBOSE = args.verbose
    if VERBOSE: configure_logging()

    session = requests.Session()
    session.headers.update({'Referer':site})

    if args.logout:
        session.get(f"{site}/api/profile")
        set_csrf_header(session)
        do_logout(session)
        return

    load_cookies(session)
    resp = session.get(f"{site}/api/profile")
    set_csrf_header(session)
    rst = resp.json() if resp.ok else {}
    if not(rst.get('error') is None and rst.get('data') is not None):
        u,p = prompt_credentials()
        tc = check_tfa_required(session,u)
        code=None
        if tc:
            while True:
                c=input("2FA code: ")
                if re.fullmatch(r"\d{6}",c): code=c;break
        if not do_login(session,u,p,code): print("Login failed"); return
        print("Login successful.")

    if args.mode:
        cids = list_contests(session,args.mode)
        if not cids: print("No contests"); return
        while True:
            print("Select contest id: ", file=sys.stderr, end='')
            ch=input()
            if ch.isdigit() and int(ch) in cids: cid=int(ch); break
        ranks = fetch_all_ranks(session,cid)
        if args.mode.upper()=="OI":
            results_to_csv_oi(ranks)
        else:
            results_to_csv_acm(ranks)
    else:
        print("Authenticated successfully.")

if __name__=='__main__':
    main()

