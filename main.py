import config

from crawlers import aging_theory_crawler, pubmed, pmc

if __name__ == "__main__":
    n_max_papers = 1000  # Optional: maximum number of papers to retrieve
    # date_from = "2020/01/01"  # Optional: start date
    # date_to = "2026/01/01"  # Optional: end date

    pubmed_email = config.NCBI_EMAIL
    pubmed_api_key = config.NCBI_API_KEY
    pubmed_crawler = pubmed.PubmedCrawler(email=pubmed_email, api_key=pubmed_api_key,
                                            max_papers=n_max_papers,
                                            # date_from=date_from,
                                            # date_to=date_to,
                                            )

    # scopus_token = config.SCOPUS_TOKEN
    # scopus_crawler = aging_theory_crawler.ScopusCrawler(api_token=scopus_token)  # Add when ready

    # nature_email=config.NATURE_EMAIL
    # nature_=''
    # nature_crawler = aging_theory_crawler.NatureCrawler(email="me@uni.edu")

    pmc_email = config.PMC_EMAIL
    pmc_api_key = config.PMC_API_KEY
    pmc_crawler = pmc.PmcCrawler(email=pmc_email, api_key=pmc_api_key,
                                 max_papers=n_max_papers
                                 # date_from=date_from,
                                 # date_to=date_to,
                                 )

    all_crawlers = [
        pubmed_crawler,
        pmc_crawler,
        # scopus_crawler,
        # nature_crawler,
        ]
    main_crawler = aging_theory_crawler.AgingTheoryCrawler(crawlers=all_crawlers)

    df = main_crawler.run_comprehensive_search()
    main_crawler.save_results(df)