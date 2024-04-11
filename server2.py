# Import necessary modules
from flask import Flask, render_template, jsonify
from sqlalchemy import create_engine, Column, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from scrapy.crawler import CrawlerProcess
from scrapy.spiders import Spider
from scrapy.http import Request
import os
from pathlib import Path

import uuid
from PyPDF2 import PdfReader

import scrapy
from scrapy import Request
from scrapy.crawler import CrawlerProcess
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
import tabula
import pandas as pd



# Define Flask app
app = Flask(__name__)
PDF_FOLDER = 'pdf_files'
app.config['PDF_FOLDER'] = PDF_FOLDER

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

# Define Scrapy spider to download PDF and extract text
class PDFSpider(Spider):
    name = 'pdf_spider'
    start_urls = ['https://www.jornalminasgerais.mg.gov.br']

    def __init__(self):
        self.cursor: None
        chrome_options = Options()
        prefs = {'download.default_directory':'C:\\Users\\CABRERA-PC\\dev2024\\jornacoletor\\pdf_files'} #UPDATE ADDRESS CORRESPONDING TO THE MACHINE, FOLDER MUST BE NAMED pdf_files
        chrome_options.add_experimental_option('prefs', prefs)
        self.driver = webdriver.Chrome(options=chrome_options)

    def start_requests(self):
        url = self.start_urls[0]
        self.driver.get(url)
        time.sleep(3)
        self.driver.find_element(By.ID, "linkDownloadPDF").click()
        time.sleep(4)
        yield scrapy.Request(url, self.parse)

    def parse(self, response):
        pdf_url = response.xpath('//*[@id="linkDownloadPDF"]/@href').get()
        if pdf_url:
             yield Request(pdf_url, callback=self.save_pdf)
        else:
            self.logger.error('PDF URL not found on the webpage')


    def save_pdf(self, response):
        content_disposition = response.headers.get('Content-Disposition')
        if content_disposition:
            pdf_id = str(uuid.uuid4())
            file_name = content_disposition.split('filename=')[-1].strip('"')
            file_path = os.path.join('C:\\Users\\CABRERA-PC\\dev2024\\jornacoletor\\pdf_files', file_name)#UPDATE ADDRESS CORRESPONDING TO THE MACHINE, FOLDER MUST BE NAMED pdf_files
            print("File path found:", file_path)
            with open(file_path, 'wb') as f:
                f.write(response.body)
            
            pdf_text = self.extract_text_from_pdf(file_path)
            os.remove(file_path)  # Remove downloaded PDF file
            
            with Session() as session:
                pdf_entry = PDFText(id=pdf_id, text=pdf_text)
                session.add(pdf_entry)
                session.commit()
        else:
            print("Content-Disposition header not found. Unable to determine file name.")


    



# Flask route to display PDF texts
@app.route('/')
def index():
    pdf_texts = {}
    pdf_folder = app.config['PDF_FOLDER']
    for filename in os.listdir(pdf_folder):
        if filename.endswith('.pdf'):
            filepath = os.path.join(pdf_folder, filename)
            pdf_reader = PdfReader(filepath)
            text = ''
            for page in pdf_reader.pages:
                text += page.extract_text()
            pdf_texts[filename] = text

    return render_template('index.html', pdf_texts=pdf_texts)

# Function to start the Scrapy spider
def run_spider():
    process = CrawlerProcess(settings={
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    })
    process.crawl(PDFSpider)
    process.start()

if __name__ == "__main__":
    run_spider()  # Start the Scrapy spider
    app.run(debug=True)
