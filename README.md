# CP-term-score-calculator
A score calculator of NCCU CS CP classes

A command-line Python tool to interact with your OnlineJudge instance (e.g., QingdaoU/OnlineJudge). Supports authentication (including 2FA), session persistence via cookies, and fetching contest rankings for both ACM and OI rules, exporting them as CSV.

---

## Features

* **Login / Logout**: Securely log in (with 2FA support) and log out, persisting session cookies to a local file (`oj_api_cookies.json`) in the project directory.
* **Environment-driven**: Configure your judge URL via a `.env` file.
* **Contest Listing**: List contests by rule type (ACM or OI).
* **Rank Fetching**: Automatically paginate and aggregate rank data.
* **CSV Export**:

  * **ACM Mode**: First AC = full points, second AC = half points, more attempts = 0.
  * **OI Mode**: Direct scoring as provided by the API.
* **Verbose Debugging**: `-v/--verbose` for detailed HTTP and internal logs.

---

## Requirements

* Python 3.7+
* [requests](https://pypi.org/project/requests/)
* [python-dotenv](https://pypi.org/project/python-dotenv/)

List dependencies in `requirements.txt`:

```text
requests
python-dotenv
```

---

## Setup

1. **Clone this repository**

```bash
git clone [https://github.com/dark9ive/CP-term-score-calculator.git](https://github.com/dark9ive/CP-term-score-calculator.git)
cd CP-term-score-calculator
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Copy and write a `.env` file** in project root:
```bash
cp ./.env.example ./.env
```
### .env
```dotenv
# Base URL of your OnlineJudge instance
# e.g. https://oj.example.edu
SITE=https://oj.example.edu
```

4. **Make the script executable** (optional)

```bash
chmod +x oj_api_tool.py
```

---

## Usage

### Authentication

- **Login** (prompts credentials and optional 2FA):

```bash

python3 oj_api_tool.py

# or without mode (only authenticates):

python3 oj_api_tool.py

```

- **Logout**:

```bash
python3 oj_api_tool.py --logout
```

- **Verbose mode**:

```bash
python3 oj_api_tool.py -v --mode OI
```

### Fetch Contest Rankings

- **ACM Mode**: First AC full points, second AC half, else zero.
```bash
python3 oj_api_tool.py --mode ACM > acm_rank.csv
```

- **OI Mode**: Use direct scores from API.

```bash
python3 oj_api_tool.py --mode OI > oi_rank.csv
```

The tool will:
1. List available contests with IDs and titles.
2. Prompt you to select a contest ID.
3. Fetch and consolidate all pages of ranking data (using a 250-record page limit).
4. Output CSV to `stdout` (redirect to file as needed).

---

## File Structure

```

.
├── oj_api_tool.py       # Main script
├── requirements.txt    # Python dependencies
├── README.md           # Project documentation
├── .env                # Holds SITE variable (gitignored)
└── .oj_api_cookies.json # Session cookies stored locally (gitignored)

```

---

## Security

- Cookies stored in `.oj_api_cookies.json` in the project folder are file-permission protected (600).
- `.env` and `.oj_api_cookies.json` are ignored via `.gitignore`.

---

## License

MIT License. Feel free to adapt and extend.

```

