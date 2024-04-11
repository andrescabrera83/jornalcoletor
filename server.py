from flask import Flask, render_template
from sqlalchemy import create_engine, Column, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import scrapy
from scrapy import Request
from scrapy.crawler import CrawlerProcess
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
import tabula
import pandas as pd


app = Flask(__name__)

# Define SQLAlchemy models
Base = declarative_base()

class PDFText(Base):
    __tablename__ = 'pdf_texts'
    id = Column(String, primary_key=True)
    text = Column(String)

# Establish connection with the database
engine = create_engine('sqlite:///pdf_texts.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()


class RpaDiarioOficialMG(scrapy.Spider):
    name = "diario-oficial-mg"
    base_url = "https://www.jornalminasgerais.mg.gov.br"

    def __init__(self):
        self.cursor: None
        chrome_options = Options()
        prefs = {'C:\\Users\\CABRERA-PC\\dev2024\\jornacoletor\\pdfs'}
        chrome_options.add_experimental_option('prefs', prefs)
        self.driver = webdriver.Chrome(options=chrome_options)

    def start_requests(self):
        url = self.base_url
        self.driver.get(url)
        time.sleep(3)
        self.driver.find_element(By.ID, "linkDownloadPDF").click()
        time.sleep(4)
        yield scrapy.Request(url, self.parse)

    def parse(self, response):
        pdf_url = response.xpath('//*[@id="linkDownloadPDF"]/@href').get()

        if pdf_url:
            yield Request(
                url=pdf_url,
                callback=self.save_pdf,
                meta={response: response}

            )

    def save_pdf(self, response):
        
        file_path = 'C:\\Users\\CABRERA-PC\\dev2024\\jornacoletor\\pdfs\\document.pdf'
        with open(file_path, 'wb') as f:
            f.write(response.body)
        yield {'file_path': file_path}

        pdf_file = file_path
        lista_pdf = tabula.read_pdf(pdf_file, pages='all')
        print(len(lista_pdf))
        self.driver.quit()

        for page in lista_pdf:
            text = ' '.join(page)
            pdf_entry = PDFText(id=pdf_file, text=text)
            session.add(pdf_entry)
        session.commit()


        
        print("Text extracted and stored successfully.")


def main():

    # Create a CrawlerProcess with your settings
    process = CrawlerProcess({
        'USER_AGENT': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1)'
    })

    # Start the web scraping process
    process.crawl(RpaDiarioOficialMG)

    # Start the crawler
    process.start()


# Function to retrieve PDF texts from the database
def get_pdf_texts():
    # Create a session object
    session = Session()
    # Query the database to retrieve all rows from the pdf_texts table
    pdf_texts = session.query(PDFText).all()
    # Close the session
    session.close()
    # Convert the PDF texts to a serializable format (e.g., list of dictionaries)
    pdf_texts_serializable = [{'id': pdf_text.id, 'text': pdf_text.text} for pdf_text in pdf_texts]
    # Return the queried PDF texts
    return pdf_texts_serializable

# Flask route to display text from PDF
@app.route('/')
def index():

    pdf_texts = get_pdf_texts()

    # Render template with PDF text
    return render_template('index.html', pdf_text=pdf_texts)

if __name__ == "__main__":
    main()
    app.run(debug=True)
