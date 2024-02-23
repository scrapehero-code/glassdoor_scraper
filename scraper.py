import argparse
import asyncio

import unicodecsv as csv
from lxml import html
from playwright.async_api import Playwright, async_playwright


async def run(playwright: Playwright, keyword: str, place: str) -> None:
    """Collecting details of all jobs in the provided keyword and place

    Args:
        keyword (String): _Job title to search
        place (String): Location to search

    Returns:
        Dict: Details of each job
    """
    browser = await playwright.chromium.launch(headless=False)
    context = await browser.new_context()
    page = await context.new_page()
    place_len = str(len(place) + 1)
    url_len = str(len(keyword + place) + 1)
    await page.goto(
        f"https://www.glassdoor.com/Job/{place}-{keyword}-jobs-SRCH_IL.0,12_IC1154532_KO{place_len},{url_len}.htm",
        wait_until="load",
    )
    response = await page.content()
    # Collecting urls to each job description page
    tree = html.fromstring(response)
    links = tree.xpath('//a[@class="JobCard_jobTitle__rbjTE"]/@href')
    job_listings = []
    # Visiting each url and collecting data
    for link in links:
        try:
            page = await context.new_page()
            await page.goto(link, wait_until="load")
            response = await page.content()
            tree = html.fromstring(response)
            company_name = tree.xpath(
                '//div[@class="JobDetails_jobDetailsHeader__qKuvs"]/a/div/span/text()'
            )[0]
            role = tree.xpath(
                '//div[@class="JobDetails_jobDetailsHeader__qKuvs"]/h1/text()'
            )[0]
            location = tree.xpath(
                '//div[@class="JobDetails_jobDetailsHeader__qKuvs"]/div/text()'
            )[0]
            city = location.split(",")[1]
            state = location.split(",")[0]
            salary = tree.xpath(
                '//div[@class="SalaryEstimate_averageEstimate__xF_7h"]/text()'
            )
            if salary:
                salary = salary[0].split("$")[1]
            else:
                salary = "N/A"
            jobs = {
                "Name": role,
                "Company": company_name,
                "City": city,
                "State": state,
                "Salary": salary,
                "Location": location,
                "Url": link,
            }
            job_listings.append(jobs)
            await page.wait_for_timeout(timeout=6000)
            await page.close()
        except Exception as e:
            print("failed to load page")
            print(e)

    # ---------------------
    await context.close()
    await browser.close()
    return job_listings


async def main(keyword: str, place: str) -> dict:
    async with async_playwright() as playwright:
        job_listings = await run(playwright, keyword, place)
        return job_listings


def parse(keyword: str, place: str) -> dict:
    """
    Args:
        keyword (str): Job title to be search
        place (str): Job description to be searched
    
    Returns:
        Dict: Details of each job
    """
    job_listings = asyncio.run(main(keyword, place))
    return job_listings


if __name__ == "__main__":

    """eg-:python glassdoor.py "android-developer", "boston-ma" """

    argparser = argparse.ArgumentParser()
    argparser.add_argument("keyword", help="job name", type=str)
    argparser.add_argument("place", help="job location", type=str)
    args = argparser.parse_args()
    keyword = args.keyword
    place = args.place
    print("Fetching job details")
    scraped_data = parse(keyword, place)
    print("Writing data to output file")

    with open("%s-%s-job-results.csv" % (keyword, place), "wb") as csvfile:
        fieldnames = ["Name", "Company", "State", "City", "Salary", "Location", "Url"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        if scraped_data:
            for data in scraped_data:
                writer.writerow(data)
        else:
            print(
                "Your search for %s, in %s does not match any jobs" % (keyword, place)
            )
