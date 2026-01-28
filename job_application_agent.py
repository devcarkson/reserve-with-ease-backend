import time
import os
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from urllib.parse import quote

# LinkedIn credentials (use environment variables for security)
LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL") or input("Enter LinkedIn email: ")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD") or input("Enter LinkedIn password: ")

# Job search parameters
KEYWORDS = "Python Developer OR Backend Developer OR Full Stack Engineer"
LOCATION = "Lagos, Nigeria"
MAX_JOBS = 20

def login_linkedin(driver):
    driver.get("https://www.linkedin.com/login")
    time.sleep(2)
    email_field = driver.find_element(By.ID, "username")
    email_field.send_keys(LINKEDIN_EMAIL)
    password_field = driver.find_element(By.ID, "password")
    password_field.send_keys(LINKEDIN_PASSWORD)
    password_field.send_keys(Keys.RETURN)
    time.sleep(5)  # Wait for login

def search_jobs(driver):
    # Use direct search URL to avoid element finding issues
    keywords_encoded = quote(re.sub(r' ', '%20', re.sub(r'OR', '%20OR%20', KEYWORDS)))
    location_encoded = quote(re.sub(r' ', '%20', LOCATION))
    search_url = f"https://www.linkedin.com/jobs/search/?keywords={keywords_encoded}&location={location_encoded}"
    driver.get(search_url)
    time.sleep(5)

def get_job_listings(driver):
    # Wait for page to load and try different selectors
    try:
        # Wait a bit longer for page to load
        time.sleep(5)
        
        # Print page title for debugging
        print(f"Current page title: {driver.title}")
        
        # Try many possible selectors for LinkedIn job cards
        selectors = [
            # Updated selectors for LinkedIn 2024
            ".jobs-search-results-list__item",
            ".job-card-container",
            ".job-search-card",
            "[data-job-id]",
            ".job-search-card__item-wrapper",
            ".job-search-card__item",
            ".base-card",
            ".jobs-search__results-list li",
            ".job-list__item",
            "[class*='job-card']",
            "[class*='job-search']",
            "[data-urn*='job']"
        ]
        
        jobs = []
        for selector in selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                print(f"Found {len(elements)} elements with selector: {selector}")
                if elements:
                    jobs = elements
                    break
            except Exception as e:
                print(f"Selector {selector} failed: {e}")
                continue
        
        if not jobs:
            # Try to find any links that look like job postings
            try:
                all_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/jobs/view/']")
                print(f"Found {len(all_links)} job links")
                if all_links:
                    # Extract job data from links
                    for link in all_links[:MAX_JOBS]:
                        try:
                            job_element = link.find_element(By.XPATH, "..")
                            title = job_element.get_attribute("aria-label") or job_element.text.strip()
                            company = "Unknown Company"
                            
                            # Try to find company name
                            try:
                                company_elem = job_element.find_element(By.CSS_SELECTOR, ".t-14.t-normal")
                                if company_elem:
                                    company = company_elem.text.strip()
                            except:
                                pass
                            
                            href = link.get_attribute("href")
                            if title and href:
                                jobs.append({"title": title, "company": company, "link": href})
                        except Exception as e:
                            print(f"Error processing job link: {e}")
                            continue
            except Exception as e:
                print(f"Error finding job links: {e}")
        
        if not jobs:
            print("Could not find any job listings. LinkedIn may have changed their structure.")
            print("Current URL:", driver.current_url)
            # Save screenshot for debugging
            try:
                driver.save_screenshot("linkedin_debug.png")
                print("Screenshot saved as linkedin_debug.png")
            except:
                pass
        
        # Process jobs to extract proper data
        job_data = []
        for job in jobs[:MAX_JOBS]:
            try:
                # Get link first
                link_element = job.find_element(By.TAG_NAME, "a")
                link = link_element.get_attribute("href") if link_element else None

                # Get title from link element
                title = link_element.get_attribute("aria-label") or link_element.text.strip()

                if not title:
                    # Try different title selectors
                    title_selectors = ["job-search-card__title", "job-card-list__title", "base-search-card__title"]
                    for title_sel in title_selectors:
                        try:
                            title = job.find_element(By.CLASS_NAME, title_sel).text
                            break
                        except:
                            continue

                if not title:
                    title = job.find_element(By.TAG_NAME, "h3").text

                # Clean title
                title = re.sub(r'\s+', ' ', title).strip()

                # Try different company selectors
                company_selectors = ["job-search-card__company-name", "job-card-container__company-name", "base-search-card__subtitle", ".t-14.t-normal"]
                company = None
                for company_sel in company_selectors:
                    try:
                        if company_sel.startswith('.'):
                            company = job.find_element(By.CSS_SELECTOR, company_sel).text
                        else:
                            company = job.find_element(By.CLASS_NAME, company_sel).text
                        break
                    except:
                        continue

                if not company:
                    company = "Unknown Company"

                # Clean company
                company = re.sub(r'\s+', ' ', company).strip()

                if title and link:
                    job_data.append({"title": title, "company": company, "link": link})
            except Exception as e:
                print(f"Error processing job: {e}")
                continue
        
        return job_data
        
    except Exception as e:
        print(f"Error in get_job_listings: {e}")
        return []

def apply_to_job(driver, job):
    driver.get(job["link"])
    time.sleep(3)
    try:
        # Try different apply button selectors
        apply_selectors = [
            "//button[contains(@class, 'jobs-apply-button')]",
            "//button[contains(@class, 'apply-button')]",
            "//button[contains(text(), 'Apply')]",
            "//a[contains(text(), 'Apply')]",
            "//button[contains(@aria-label, 'Apply')]",
            "//a[contains(@aria-label, 'Apply')]",
            "//button[@data-control-name='jobdetails_topcard_primary_apply']",
            "//a[@data-control-name='jobdetails_topcard_primary_apply']"
        ]
        
        apply_button = None
        for selector in apply_selectors:
            try:
                apply_button = driver.find_element(By.XPATH, selector)
                break
            except:
                continue
        
        if apply_button:
            apply_button.click()
            time.sleep(2)
            
            # Handle easy apply form if present
            if "easy-apply" in driver.current_url.lower():
                try:
                    submit_button = driver.find_element(By.XPATH, "//button[@type='submit']")
                    submit_button.click()
                    print(f"Applied to {job['title']} at {job['company']}")
                except:
                    print(f"Easy apply form found, but could not submit for {job['title']}")
            else:
                print(f"Manual application required for {job['title']} at {job['company']}")
        else:
            print(f"Could not find apply button for {job['title']} at {job['company']}")
    except Exception as e:
        print(f"Could not apply to {job['title']} at {job['company']}: {e}")

def main():
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    try:
        login_linkedin(driver)
        search_jobs(driver)
        jobs = get_job_listings(driver)
        
        if not jobs:
            print("No jobs found")
            return
        
        applied_count = 0
        for job in jobs:
            print(f"\nJob: {job['title']} at {job['company']}")
            confirm = input("Apply? (y/n): ")
            if confirm.lower() == 'y':
                apply_to_job(driver, job)
                applied_count += 1
                if applied_count >= MAX_JOBS:
                    print(f"Applied to {applied_count} jobs. Stopping.")
                    break
            time.sleep(2)
        
        print(f"\nTotal applications: {applied_count}")
    except Exception as e:
        print(f"Error in main process: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
