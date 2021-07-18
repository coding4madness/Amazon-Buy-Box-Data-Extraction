# -*- coding: utf-8 -*-
import urllib3, sys, os
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from time import sleep
from bs4 import BeautifulSoup
from collections import defaultdict
import pandas as pd
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import *
from selenium.webdriver.common.by import By
import re
from datetime import datetime
import Get_Seller_Profile
import numpy as np

output_path = os.path.dirname(os.path.realpath(__file__)) + '/output'

def getSellerPrice(page, category1, category2):
    # Create webdriver object
    driver = webdriver.Chrome(executable_path='chromedriver.exe')
    # Get the website
    driver.get(page)
    resultCount = WebDriverWait(driver, 50).until(EC.presence_of_element_located((By.XPATH, '//span[@id="aod-filter-offer-count-string"]'))).text
    maxCount = re.findall('\d+', resultCount)
    try:
        scrollCount = round(int(maxCount[0]) / 10)
    except IndexError:
        scrollCount = 0

    def cleanFilename(name):
        invalid = '<>:"/\|?*'
        for char in invalid:
            name = name.replace(char, '')
        return name[0:180]

    i = 0
    while i <= scrollCount + 1:
        WebDriverWait(driver, 5000).until(EC.presence_of_element_located((By.XPATH, '//div[@class="a-scroller a-scroller-vertical"]'))).click()
        driver.find_element_by_tag_name('body').send_keys(Keys.END)
        i = i + 1
        try:
            WebDriverWait(driver, 50).until(EC.presence_of_element_located((By.XPATH, '//a[@id="aod-show-more-offers"]'))).click()
        except (NoSuchElementException, TimeoutException, ElementNotInteractableException):
            pass
        sleep(3)

    driver.find_element_by_tag_name('body').send_keys(Keys.HOME)

    productCondition = []
    productPrice = []
    productShipping = []
    productShippingFastest = []
    productSeller = []
    productShipper = []
    profileSeller = []

    soup = BeautifulSoup(driver.page_source, features='lxml')

    # Buy Box
    for buyBox in soup.find_all('div', attrs={'id':'aod-pinned-offer'}):
        title = soup.find_all('h5', attrs={'id':'aod-asin-title-text'})[0].text.strip()
        for condition in buyBox.find_all('div', attrs={'id':'aod-offer-heading'}):
            productCondition.append(condition.text.replace('\n', ' ').strip())
        for prices in buyBox.find_all('div', attrs={'id':'aod-price-0'}):
            for price in prices.find_all('span', attrs={'class':'a-price'}):
                productPrice.append(price.find_all('span', attrs={'class':'a-offscreen'})[0].text.replace('\n', ' ').strip())
        for delivery in buyBox.find_all('div', attrs={'id':'fast-track-message'}):
            for shipping in delivery.find_all('div', attrs={'id':'delivery-message'}):
                regularDelivery = ' '.join(shipping.text.splitlines()).strip()
                productShipping.append(re.sub(' +', ' ', regularDelivery))
            if delivery.find_all('div', attrs={'id':'upsell-message'}) == []:
                productShippingFastest.append('')
            else:
                for shippingFastest in delivery.find_all('div', attrs={'id':'upsell-message'}):
                    fastestDelivery = ' '.join(shippingFastest.text.splitlines()).strip()
                    productShippingFastest.append(re.sub(' +', ' ', fastestDelivery))
        for seller in buyBox.find_all('div', attrs={'id':'aod-offer-soldBy'}):
            merchant = re.sub(r'\([^()]*\)[0-9]+% positive over last [0-9]+ months', '', seller.text.replace('\n', ' ').replace('Sold by', '').replace('-', '').strip()).strip()
            productSeller.append(merchant)
            try:
                profileSeller.append('https://www.amazon.com' + seller.find_all('a')[0].get('href'))
            except IndexError:
                profileSeller.append('None')
        for shipper in buyBox.find_all('div', attrs={'id':'aod-offer-shipsFrom'}):
            productShipper.append(shipper.text.replace('\n', ' ').replace('Ships from', '').replace('-', '').strip())

    # Other 3P Sellers
    for offer in soup.find_all('div', attrs={'id':'aod-offer'}):
        for condition in offer.find_all('div', attrs={'id':'aod-offer-heading'}):
            productCondition.append(condition.text.replace('\n', ' ').strip())
        for prices in offer.find_all('div', attrs={'id':'aod-offer-price'}):
            for price in prices.find_all('span', attrs={'class':'a-price'}):
                productPrice.append(price.find_all('span', attrs={'class':'a-offscreen'})[0].text.replace('\n', ' ').strip())
        for delivery in offer.find_all('div', attrs={'id':'fast-track-message'}):
            for shipping in delivery.find_all('div', attrs={'id':'delivery-message'}):
                regularDelivery = ' '.join(shipping.text.splitlines()).strip()
                productShipping.append(re.sub(' +', ' ', regularDelivery))
            if delivery.find_all('div', attrs={'id':'upsell-message'}) == []:
                productShippingFastest.append('')
            else:
                for shippingFastest in delivery.find_all('div', attrs={'id':'upsell-message'}):
                    fastestDelivery = ' '.join(shippingFastest.text.splitlines()).strip()
                    productShippingFastest.append(re.sub(' +', ' ', fastestDelivery))
        for seller in offer.find_all('div', attrs={'id':'aod-offer-soldBy'}):
            merchant = re.sub(r'\([^()]*\).*', '', seller.text.replace('\n', ' ').replace('Sold by', '').replace('-', '').strip()).strip()
            productSeller.append(merchant)
            try:
                profileSeller.append('https://www.amazon.com' + seller.find_all('a')[0].get('href'))
            except IndexError:
                profileSeller.append('None')
        for shipper in offer.find_all('div', attrs={'id':'aod-offer-shipsFrom'}):
            productShipper.append(shipper.text.replace('\n', ' ').replace('Ships from', '').replace('-', '').strip())

    dict = defaultdict(list)

    data = list(zip(productSeller, productShipper, productCondition, productPrice, productShipping, productShippingFastest, profileSeller))
    df = pd.DataFrame(data, columns = ['Seller', 'Shipper', 'Condition', 'Price', 'Delivery', 'Fastest Delivery', 'Seller Page'])
    donetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    ts = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    df = df[df['Condition'] == 'New']
    df['Product Name'] = title
    df['Product Category 1'] = category1
    df['Product Category 2'] = category2
    df['Timestamp'] = donetime
    df['Merchant ID'] = df['Seller Page'].apply(Get_Seller_Profile.getSellerID)
    df['Merchant ID'] = df['Merchant ID'].apply(lambda x: 'Amazon.com' if x == '' else x)
    df['ASIN'] = df['Seller Page'].apply(Get_Seller_Profile.getASIN)
    df['ASIN'] = df['ASIN'].apply(lambda x: np.NaN if x == '' else x)
    df['ASIN'] = df['ASIN'].fillna(method='ffill').fillna(method='bfill')
    df['Seller Profile'] = df['Seller Page'].apply(Get_Seller_Profile.getSellerProfile)
    df['Positive 30 days'], df['Positive 90 days'], df['Positive 12 months'], df['Lifetime'], df['Total ratings'] = zip(*df['Seller Page'].apply(Get_Seller_Profile.getSellerProfile2))
    df['Buy Box Placement'] = df.apply(lambda x: 'True' if x.name == 0 else 'False', axis=1)
    df.to_csv(output_path + '/' + cleanFilename(title) + ' ' + ts + '.csv', index=False, encoding='utf-8')

    driver.close()