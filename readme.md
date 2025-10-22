In this readme you will find:
an overview of the project, what it does, what the limitations
how to run this project
what the possibel futur directions

# Aging Theory Research Assistant 🧬
Effortlessly collect, organize, and analyze scientific papers on aging theories – across major databases.

This project helps researchers collect and analyze scientific papers about aging theories from major academic databases. Think of it as a smart research assistant that automatically finds and organizes aging-related research papers.

## Why This Matters 🎯
- **Save Time**: What would take weeks to collect manually can be done in hours
- **Stay Current**: Automatically find the newest research about aging theories (need a server)
- **Comprehensive**: Searches across multiple scientific databases
- **Organized**: All papers are neatly organized and easy to analyze

## What It Does 🔍
1. **Collects Papers**: Pulls papers on aging from sources like PubMed, PMC, and more (additions easy).

2. **Extracts Key Details**: For each paper: title, abstract, year, keywords, links/full text, DOI.

3. **Delivers Usable Data**: Results go directly to clean CSV files compatible with Excel, Google Sheets, and data pipelines

## Getting Started 🚀

### Prerequisites
- Python 3.8 or newer
- Internet connection
- NCBI (PubMed) API key (free)

### Quick Start
1. **Setup**:
   ```bash
   # Clone the repository
   git clone https://github.com/blackbalancef/aging-theories.git
   ```
   ```bash
   # Create enviroment 
   python3 -m venv .venv
   source .venv/bin/activate   # on macOS/Linux
   .venv\Scripts\activate      # on Windows
   ```
   ```bash
   # Install required packages
   pip install -r requirements.txt
   ```
2. **Configure**:
   - Create a `.env` file in the root of the project
   - Add your API keys into `.env`
   - Add your search topics in `input/topics.txt`
   - Add your search queries in `input/queries.txt`

3. **Adjust if needed**
   In the `main.py` file add the neccecary information, such as:
   - number of papers per query in the 'input/queries.txt'
   - date from
   - date to

4. **Run**:
   ```bash
   python main.py
   ```

## Project Structure 📁
aging_theory_crawler/

├── input/           # Search topics and queries

├── data_output/     # Your collected results will be there once you run

├── example_output/     # Example of collected results

├── crawlers/        # Main & database-specific crawlers

├── config.py        # API keys and settings from the `.env` you created

└── main.py          # Entrypoint, Run crawlers here

More detailed:

input/ # Your search configuration
- topics.txt # Research topics to search for 
- queries.txt # Detailed search queries

example_output/ # Example of saved results
- file.csv # Results of the search

data_output/ # Where your results are saved
- file.csv # Results of the search

crawlers/ # Where all crawlers are saved
- aging_theory_crawler.py # Main crawler code 
- pubmed.py # PubMed specific code 
- pmc.py # PMC specific code 


## Search Topics 🔬
We search for papers related to:
- General aging theories
- Cellular senescence
- DNA damage and repair
- Telomeres
- Oxidative stress
- And many more...

## Limitations
- API rate limits: Built-in delays to avoid bans; 
- Large-scale runs limited by recent team formation (after prior teams dissolved).
- Hackathon Mode: Used pre-set queries for speed – fully configurable for production.

## Results 📊
- Results are saved as CSV files in the `data_output` folder
- Each file is named with the date and time of the search
- Easy to open in Excel, Google Sheets, or similar programs

## Contributing 🤝
We welcome contributions! If you'd like to help:
1. Fork the repository
2. Create a new branch
3. Make your changes
4. Submit a pull request

## Need Help? 💡
- Open an issue for bug reports
- Contact the maintainers for questions

## License 📜
This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments 🙏
- NCBI for PubMed and PMC access
- Nature Publishing Group

Made with ❤️ by bioloshki team:

Mariia BAI,
Ivan MATVEEV

For the HackAging: Theories of Aging Challenge https://www.hackaging.ai/
Challenge: THEORIES OF AGING https://www.hackaging.ai/challenges/aging-theories/

------
## API Key
### Benefits of API Key:

10 requests/second (vs 3 without key)

3.3x faster data collection

Required for large-scale retrieval

### API KEYS setup
Get NCBI API Key:

1.Create NCBI account: https://account.ncbi.nlm.nih.gov/

2.Sign in → Click username (top right) → Account Settings

3.Scroll to "API Key Management" → Click "Create an API Key"

4.Copy the key

5. Create ".env" file or you can directly write your credentials to config.py.
```
NCBI_EMAIL='your@email.com'
NCBI_API_KEY='your_key'
```
6. Don't forget to remove it when you push it.

7. You can add more topics in the 'input/topics.txt', or write your queries directly in 'queries.txt', keeping the same writing style

We would use wildcards for variations (see example in 'input/queries.txt'):

mechanism*  → matches mechanism, mechanisms, mechanistic

theor*      → matches theory, theories, theoretical

-----------------
### Limitations:
To avoid bans, we had to include delays between requests, which limited how much we could run. Since our team was only finalized a few days ago (after two teams dropped out), we didn’t have time for large-scale runs.

#### Europe PMC

https://dev.springernature.com/register/
The Basic OA API will usually provide for a rate limit of 500 hits / day and 100 hits / min.Basic OA API Access Key will usually provide for up to 8 constraints.Publisher endeavors to achieve the aforementioned performance, but does not make any warranty as to the availability or performance of the Basic OA APIs.For security reasons Publisher may exchange the Access Key any time at Publisher’s discretion

Rate limits for both APIs are 500 hits/day and 100 hits/minute, with up to 8 constraints per key.
API Rate Limits Explained
Springer Nature sets rate limits for both the Open Access API and the Metadata API to protect system resources and ensure fair usage:

Daily Limit: You can make up to 500 requests per day with a single API key.

Minute Limit: You can make up to 100 requests per minute.

Constraints: Each API key usually supports up to 8 simultaneous constraints (which are typically filter parameters or query conditions — you’ll want to check the docs for specific use cases).

-----------------------------------------
### F.A.Q.:
What Happens If We Exceed Limits?

If we go beyond these limits, our API access may be temporarily suspended or our requests will start failing (typically with a rate limit error). Circumventing these restrictions by creating multiple accounts or API keys is explicitly forbidden and may lead to permanent suspension.

Tips for Maximizing Paper Collection
Plan downloads: Spread requests evenly to avoid hitting the limits all at once. For example, if we want to collect many papers, we should consider running our scripts overnight and batching requests.

Optimizing queries: Each API request should retrieve as much relevant data as possible. We should use the documentation to learn how to get all metadata with a single query (for example, paginating effectively).

No circumvention: Do not try to register multiple keys or accounts to bypass limits; the agreement strictly forbids this, and Springer Nature can revoke access for violations.

Remember:

500 hits/day, 100 hits/minute per key

No multiple accounts or keys for one user

If at the limit, pause and try again later

-----------------------------------------

### Interesting point for NCBI:
this 2 links give the same results: 
- Canonical NCBI format: https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7612201/
- Alternate legacy PMC format: https://pmc.ncbi.nlm.nih.gov/articles/PMC7612201/

For this hackathon we kept the legacy, as it was provided in the 5 examples

-----
Future optimisations:
Possible to optimise * parts with AWS, for example.
lambda makes API calls to third-party API, write the data to Amazon S3, running on schedule

S3 stores the data
AWD Glue transforms the raw data
S3 Store clean data
Visualisation with Quicksight


Add more crawlers from the list:
PubMed,
PMC,
arXiv
Nature,
ScienceDirect,
Frontiers in Aging https://www.frontiersin.org/
CORE, Unpaywall,
Semantic Scholar Open API,
Springer, Scopus, Web of Science