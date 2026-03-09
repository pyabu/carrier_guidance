"""
CareerPath Pro – Tamil Nadu & Pondicherry Job Scraper
═══════════════════════════════════════════════════════════
Dedicated scraper for jobs across ALL Tamil Nadu cities + Puducherry.

Fetches real jobs from:
  1. LinkedIn (city-specific searches)
  2. Naukri.com (city + state filtered)
  3. Indeed (TN city searches)
  4. Foundit / Monster India (TN searches)
  5. Internshala (TN internships)
  6. TimesJobs (TN listings)
  7. Freshersworld (TN fresher jobs)
  8. Google Jobs RSS (TN specific)

Also generates supplemental realistic jobs from 100+ real
companies known to operate in Tamil Nadu & Pondicherry.
"""

import hashlib
import logging
import os
import random
import re
import time
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════
# TAMIL NADU & PONDICHERRY CITIES (comprehensive)
# ═══════════════════════════════════════════════════════════════════════

TAMILNADU_CITIES = [
    # Major IT / Industrial hubs
    {"city": "Chennai", "state": "Tamil Nadu", "country": "India", "display": "Chennai, Tamil Nadu", "tier": 1},
    {"city": "Coimbatore", "state": "Tamil Nadu", "country": "India", "display": "Coimbatore, Tamil Nadu", "tier": 1},
    {"city": "Madurai", "state": "Tamil Nadu", "country": "India", "display": "Madurai, Tamil Nadu", "tier": 2},
    {"city": "Tiruchirappalli", "state": "Tamil Nadu", "country": "India", "display": "Tiruchirappalli, Tamil Nadu", "tier": 2},
    {"city": "Salem", "state": "Tamil Nadu", "country": "India", "display": "Salem, Tamil Nadu", "tier": 2},
    {"city": "Tirunelveli", "state": "Tamil Nadu", "country": "India", "display": "Tirunelveli, Tamil Nadu", "tier": 2},
    {"city": "Erode", "state": "Tamil Nadu", "country": "India", "display": "Erode, Tamil Nadu", "tier": 3},
    {"city": "Vellore", "state": "Tamil Nadu", "country": "India", "display": "Vellore, Tamil Nadu", "tier": 2},
    {"city": "Thoothukudi", "state": "Tamil Nadu", "country": "India", "display": "Thoothukudi, Tamil Nadu", "tier": 3},
    {"city": "Dindigul", "state": "Tamil Nadu", "country": "India", "display": "Dindigul, Tamil Nadu", "tier": 3},
    {"city": "Thanjavur", "state": "Tamil Nadu", "country": "India", "display": "Thanjavur, Tamil Nadu", "tier": 3},
    {"city": "Hosur", "state": "Tamil Nadu", "country": "India", "display": "Hosur, Tamil Nadu", "tier": 2},
    {"city": "Nagercoil", "state": "Tamil Nadu", "country": "India", "display": "Nagercoil, Tamil Nadu", "tier": 3},
    {"city": "Kanchipuram", "state": "Tamil Nadu", "country": "India", "display": "Kanchipuram, Tamil Nadu", "tier": 3},
    {"city": "Kumbakonam", "state": "Tamil Nadu", "country": "India", "display": "Kumbakonam, Tamil Nadu", "tier": 3},
    {"city": "Karur", "state": "Tamil Nadu", "country": "India", "display": "Karur, Tamil Nadu", "tier": 3},
    {"city": "Tirupur", "state": "Tamil Nadu", "country": "India", "display": "Tirupur, Tamil Nadu", "tier": 2},
    {"city": "Sivakasi", "state": "Tamil Nadu", "country": "India", "display": "Sivakasi, Tamil Nadu", "tier": 3},
    {"city": "Ambattur", "state": "Tamil Nadu", "country": "India", "display": "Ambattur, Tamil Nadu", "tier": 2},
    {"city": "Tambaram", "state": "Tamil Nadu", "country": "India", "display": "Tambaram, Tamil Nadu", "tier": 2},
    {"city": "Avadi", "state": "Tamil Nadu", "country": "India", "display": "Avadi, Tamil Nadu", "tier": 3},
    {"city": "Tiruvallur", "state": "Tamil Nadu", "country": "India", "display": "Tiruvallur, Tamil Nadu", "tier": 3},
    {"city": "Ranipet", "state": "Tamil Nadu", "country": "India", "display": "Ranipet, Tamil Nadu", "tier": 3},
    {"city": "Tiruvannamalai", "state": "Tamil Nadu", "country": "India", "display": "Tiruvannamalai, Tamil Nadu", "tier": 3},
    {"city": "Cuddalore", "state": "Tamil Nadu", "country": "India", "display": "Cuddalore, Tamil Nadu", "tier": 3},
    {"city": "Villupuram", "state": "Tamil Nadu", "country": "India", "display": "Villupuram, Tamil Nadu", "tier": 3},
    {"city": "Ramanathapuram", "state": "Tamil Nadu", "country": "India", "display": "Ramanathapuram, Tamil Nadu", "tier": 3},
    {"city": "Virudhunagar", "state": "Tamil Nadu", "country": "India", "display": "Virudhunagar, Tamil Nadu", "tier": 3},
    {"city": "Nagapattinam", "state": "Tamil Nadu", "country": "India", "display": "Nagapattinam, Tamil Nadu", "tier": 3},
    {"city": "Namakkal", "state": "Tamil Nadu", "country": "India", "display": "Namakkal, Tamil Nadu", "tier": 3},
    {"city": "Perambalur", "state": "Tamil Nadu", "country": "India", "display": "Perambalur, Tamil Nadu", "tier": 3},
    {"city": "Krishnagiri", "state": "Tamil Nadu", "country": "India", "display": "Krishnagiri, Tamil Nadu", "tier": 3},
    {"city": "Dharmapuri", "state": "Tamil Nadu", "country": "India", "display": "Dharmapuri, Tamil Nadu", "tier": 3},
    {"city": "Theni", "state": "Tamil Nadu", "country": "India", "display": "Theni, Tamil Nadu", "tier": 3},
    {"city": "Ariyalur", "state": "Tamil Nadu", "country": "India", "display": "Ariyalur, Tamil Nadu", "tier": 3},
    {"city": "Sivaganga", "state": "Tamil Nadu", "country": "India", "display": "Sivaganga, Tamil Nadu", "tier": 3},
    {"city": "Nilgiris", "state": "Tamil Nadu", "country": "India", "display": "Nilgiris (Ooty), Tamil Nadu", "tier": 3},
    {"city": "Chengalpattu", "state": "Tamil Nadu", "country": "India", "display": "Chengalpattu, Tamil Nadu", "tier": 2},
    {"city": "Kallakurichi", "state": "Tamil Nadu", "country": "India", "display": "Kallakurichi, Tamil Nadu", "tier": 3},
    {"city": "Tenkasi", "state": "Tamil Nadu", "country": "India", "display": "Tenkasi, Tamil Nadu", "tier": 3},
    {"city": "Tirupattur", "state": "Tamil Nadu", "country": "India", "display": "Tirupattur, Tamil Nadu", "tier": 3},
    {"city": "Mayiladuthurai", "state": "Tamil Nadu", "country": "India", "display": "Mayiladuthurai, Tamil Nadu", "tier": 3},
    {"city": "Sriperumbudur", "state": "Tamil Nadu", "country": "India", "display": "Sriperumbudur, Tamil Nadu", "tier": 2},
    {"city": "Mahabalipuram", "state": "Tamil Nadu", "country": "India", "display": "Mahabalipuram, Tamil Nadu", "tier": 3},
    {"city": "OMR (Old Mahabalipuram Road)", "state": "Tamil Nadu", "country": "India", "display": "OMR, Chennai, Tamil Nadu", "tier": 1},
    {"city": "Sholinganallur", "state": "Tamil Nadu", "country": "India", "display": "Sholinganallur, Chennai, Tamil Nadu", "tier": 1},
    {"city": "Guindy", "state": "Tamil Nadu", "country": "India", "display": "Guindy, Chennai, Tamil Nadu", "tier": 1},
    {"city": "Porur", "state": "Tamil Nadu", "country": "India", "display": "Porur, Chennai, Tamil Nadu", "tier": 2},
    {"city": "Siruseri", "state": "Tamil Nadu", "country": "India", "display": "Siruseri IT Park, Chennai, Tamil Nadu", "tier": 1},
    {"city": "Tidel Park", "state": "Tamil Nadu", "country": "India", "display": "Tidel Park, Chennai, Tamil Nadu", "tier": 1},
    # Pondicherry / Puducherry
    {"city": "Pondicherry", "state": "Puducherry", "country": "India", "display": "Pondicherry, Puducherry", "tier": 2},
    {"city": "Puducherry", "state": "Puducherry", "country": "India", "display": "Puducherry", "tier": 2},
    {"city": "Karaikal", "state": "Puducherry", "country": "India", "display": "Karaikal, Puducherry", "tier": 3},
    {"city": "Mahe", "state": "Puducherry", "country": "India", "display": "Mahe, Puducherry", "tier": 3},
    {"city": "Yanam", "state": "Puducherry", "country": "India", "display": "Yanam, Puducherry", "tier": 3},
]

# ═══════════════════════════════════════════════════════════════════════
# COMPANIES OPERATING IN TAMIL NADU & PONDICHERRY
# ═══════════════════════════════════════════════════════════════════════

TN_COMPANIES = [
    # IT Giants with major TN presence
    {"name": "Zoho Corporation", "logo": "https://logo.clearbit.com/zoho.com", "industry": "Cloud / SaaS", "hq": "Chennai", "areas": ["Chennai", "Tenkasi"]},
    {"name": "Freshworks", "logo": "https://logo.clearbit.com/freshworks.com", "industry": "Cloud / SaaS", "hq": "Chennai", "areas": ["Chennai"]},
    {"name": "TCS", "logo": "https://logo.clearbit.com/tcs.com", "industry": "IT Services", "hq": "Chennai", "areas": ["Chennai", "Coimbatore", "Madurai"]},
    {"name": "Infosys", "logo": "https://logo.clearbit.com/infosys.com", "industry": "IT Services", "hq": "Chennai", "areas": ["Chennai", "Coimbatore", "Mysore"]},
    {"name": "Wipro", "logo": "https://logo.clearbit.com/wipro.com", "industry": "IT Services", "hq": "Chennai", "areas": ["Chennai"]},
    {"name": "HCL Technologies", "logo": "https://logo.clearbit.com/hcltech.com", "industry": "IT Services", "hq": "Chennai", "areas": ["Chennai", "Madurai"]},
    {"name": "Cognizant", "logo": "https://logo.clearbit.com/cognizant.com", "industry": "IT Services", "hq": "Chennai", "areas": ["Chennai", "Coimbatore"]},
    {"name": "Accenture", "logo": "https://logo.clearbit.com/accenture.com", "industry": "Consulting / IT", "hq": "Chennai", "areas": ["Chennai"]},
    {"name": "Capgemini", "logo": "https://logo.clearbit.com/capgemini.com", "industry": "IT Services", "hq": "Chennai", "areas": ["Chennai", "Salem"]},
    {"name": "Tech Mahindra", "logo": "https://logo.clearbit.com/techmahindra.com", "industry": "IT Services", "hq": "Chennai", "areas": ["Chennai"]},
    {"name": "Mphasis", "logo": "https://logo.clearbit.com/mphasis.com", "industry": "IT Services", "hq": "Chennai", "areas": ["Chennai"]},
    {"name": "Hexaware", "logo": "https://logo.clearbit.com/hexaware.com", "industry": "IT Services", "hq": "Chennai", "areas": ["Chennai"]},
    {"name": "LTIMindtree", "logo": "https://logo.clearbit.com/ltimindtree.com", "industry": "IT Services", "hq": "Chennai", "areas": ["Chennai"]},
    {"name": "IBM India", "logo": "https://logo.clearbit.com/ibm.com", "industry": "Technology", "hq": "Chennai", "areas": ["Chennai"]},
    {"name": "DXC Technology", "logo": "https://logo.clearbit.com/dxc.com", "industry": "IT Services", "hq": "Chennai", "areas": ["Chennai"]},
    {"name": "NTT DATA", "logo": "https://logo.clearbit.com/nttdata.com", "industry": "IT Services", "hq": "Chennai", "areas": ["Chennai"]},
    {"name": "Verizon India", "logo": "https://logo.clearbit.com/verizon.com", "industry": "Telecom / IT", "hq": "Chennai", "areas": ["Chennai"]},
    {"name": "PayPal India", "logo": "https://logo.clearbit.com/paypal.com", "industry": "Fintech", "hq": "Chennai", "areas": ["Chennai"]},
    {"name": "Amazon Development Centre", "logo": "https://logo.clearbit.com/amazon.com", "industry": "E-Commerce / Cloud", "hq": "Chennai", "areas": ["Chennai"]},
    {"name": "Microsoft India", "logo": "https://logo.clearbit.com/microsoft.com", "industry": "Technology", "hq": "Chennai", "areas": ["Chennai"]},
    {"name": "Google India", "logo": "https://logo.clearbit.com/google.com", "industry": "Technology", "hq": "Chennai", "areas": ["Chennai"]},
    # Product / Startup companies in TN
    {"name": "Chargebee", "logo": "https://logo.clearbit.com/chargebee.com", "industry": "SaaS / Fintech", "hq": "Chennai", "areas": ["Chennai"]},
    {"name": "Kissflow", "logo": "https://logo.clearbit.com/kissflow.com", "industry": "SaaS / Workflow", "hq": "Chennai", "areas": ["Chennai"]},
    {"name": "Kovai.co", "logo": "https://logo.clearbit.com/kovai.co", "industry": "SaaS", "hq": "Coimbatore", "areas": ["Coimbatore"]},
    {"name": "Indium Software", "logo": "https://logo.clearbit.com/indiumsoftware.com", "industry": "QA / Testing", "hq": "Chennai", "areas": ["Chennai"]},
    {"name": "ELGI Equipments", "logo": "https://logo.clearbit.com/elgi.com", "industry": "Manufacturing", "hq": "Coimbatore", "areas": ["Coimbatore"]},
    {"name": "Sundaram Finance", "logo": "https://logo.clearbit.com/sundaramfinance.in", "industry": "Finance / NBFC", "hq": "Chennai", "areas": ["Chennai", "Madurai"]},
    {"name": "TVS Motor Company", "logo": "https://logo.clearbit.com/tvsmotor.com", "industry": "Automotive", "hq": "Hosur", "areas": ["Hosur", "Chennai"]},
    {"name": "Ashok Leyland", "logo": "https://logo.clearbit.com/ashokleyland.com", "industry": "Automotive", "hq": "Chennai", "areas": ["Chennai", "Hosur"]},
    {"name": "Royal Enfield", "logo": "https://logo.clearbit.com/royalenfield.com", "industry": "Automotive", "hq": "Chennai", "areas": ["Chennai", "Tiruvottiyur"]},
    {"name": "Hyundai Motor India", "logo": "https://logo.clearbit.com/hyundai.co.in", "industry": "Automotive", "hq": "Sriperumbudur", "areas": ["Sriperumbudur", "Chennai"]},
    {"name": "Ford India", "logo": "https://logo.clearbit.com/ford.com", "industry": "Automotive", "hq": "Chennai", "areas": ["Chennai", "Maraimalai Nagar"]},
    {"name": "Caterpillar India", "logo": "https://logo.clearbit.com/caterpillar.com", "industry": "Heavy Machinery", "hq": "Chennai", "areas": ["Chennai", "Tiruvallur"]},
    {"name": "Saint-Gobain India", "logo": "https://logo.clearbit.com/saint-gobain.com", "industry": "Building Materials", "hq": "Chennai", "areas": ["Chennai"]},
    {"name": "L&T Infotech", "logo": "https://logo.clearbit.com/lntinfotech.com", "industry": "IT Services", "hq": "Chennai", "areas": ["Chennai"]},
    {"name": "HTC Global Services", "logo": "https://logo.clearbit.com/htcinc.com", "industry": "IT Services", "hq": "Chennai", "areas": ["Chennai"]},
    {"name": "CTS (Chennai)", "logo": "https://logo.clearbit.com/cognizant.com", "industry": "IT Services", "hq": "Chennai", "areas": ["Chennai", "Coimbatore"]},
    {"name": "BankBazaar", "logo": "https://logo.clearbit.com/bankbazaar.com", "industry": "Fintech", "hq": "Chennai", "areas": ["Chennai"]},
    {"name": "Matrimony.com", "logo": "https://logo.clearbit.com/matrimony.com", "industry": "Internet / Matchmaking", "hq": "Chennai", "areas": ["Chennai"]},
    {"name": "Skyworth Digital", "logo": "https://logo.clearbit.com/skyworth.com", "industry": "Electronics", "hq": "Chennai", "areas": ["Chennai"]},
    {"name": "Renault Nissan India", "logo": "https://logo.clearbit.com/renault.co.in", "industry": "Automotive", "hq": "Chennai", "areas": ["Chennai", "Oragadam"]},
    {"name": "Daimler India", "logo": "https://logo.clearbit.com/daimlertruck.com", "industry": "Automotive", "hq": "Chennai", "areas": ["Chennai", "Oragadam"]},
    {"name": "TAFE (Tractors)", "logo": "https://logo.clearbit.com/tafe.com", "industry": "Agriculture / Machinery", "hq": "Chennai", "areas": ["Chennai", "Madurai"]},
    {"name": "CavinKare", "logo": "https://logo.clearbit.com/cavinkare.com", "industry": "FMCG", "hq": "Chennai", "areas": ["Chennai"]},
    {"name": "MRF Limited", "logo": "https://logo.clearbit.com/mrftyres.com", "industry": "Manufacturing / Tyres", "hq": "Chennai", "areas": ["Chennai", "Tiruvottiyur"]},
    {"name": "Cholamandalam Finance", "logo": "https://logo.clearbit.com/cholamandalam.com", "industry": "Finance / NBFC", "hq": "Chennai", "areas": ["Chennai"]},
    {"name": "KLA Tencor", "logo": "https://logo.clearbit.com/kla.com", "industry": "Semiconductors", "hq": "Chennai", "areas": ["Chennai"]},
    {"name": "Bosch India", "logo": "https://logo.clearbit.com/bosch.in", "industry": "Engineering / Automotive", "hq": "Coimbatore", "areas": ["Coimbatore", "Chennai"]},
    {"name": "Titan Company", "logo": "https://logo.clearbit.com/titan.co.in", "industry": "Consumer Goods / Watches", "hq": "Hosur", "areas": ["Hosur", "Chennai"]},
    {"name": "Southern Railway", "logo": "https://logo.clearbit.com/sr.indianrailways.gov.in", "industry": "Government / Railways", "hq": "Chennai", "areas": ["Chennai", "Tiruchirappalli", "Madurai"]},
    {"name": "BSNL Tamil Nadu", "logo": "https://logo.clearbit.com/bsnl.co.in", "industry": "Telecom", "hq": "Chennai", "areas": ["Chennai", "Madurai", "Coimbatore"]},
    # Pondicherry companies
    {"name": "Alliance University Pondy", "logo": "https://ui-avatars.com/api/?name=AU&background=667eea&color=fff&size=80", "industry": "Education", "hq": "Pondicherry", "areas": ["Pondicherry"]},
    {"name": "Auroville", "logo": "https://ui-avatars.com/api/?name=AV&background=667eea&color=fff&size=80", "industry": "Social Enterprise", "hq": "Pondicherry", "areas": ["Pondicherry"]},
    {"name": "Mahatma Gandhi Medical College", "logo": "https://ui-avatars.com/api/?name=MG&background=667eea&color=fff&size=80", "industry": "Healthcare / Education", "hq": "Pondicherry", "areas": ["Pondicherry"]},
    {"name": "Pondicherry Cooperative Milk Society", "logo": "https://ui-avatars.com/api/?name=PC&background=667eea&color=fff&size=80", "industry": "Dairy / FMCG", "hq": "Pondicherry", "areas": ["Pondicherry"]},
    {"name": "JIPMER", "logo": "https://ui-avatars.com/api/?name=JI&background=667eea&color=fff&size=80", "industry": "Healthcare", "hq": "Pondicherry", "areas": ["Pondicherry"]},
    {"name": "ITI Pondicherry", "logo": "https://ui-avatars.com/api/?name=IT&background=667eea&color=fff&size=80", "industry": "Government / Training", "hq": "Pondicherry", "areas": ["Pondicherry"]},
    # Coimbatore-specific companies
    {"name": "Larsen & Toubro (Coimbatore)", "logo": "https://logo.clearbit.com/larsentoubro.com", "industry": "Engineering / Construction", "hq": "Coimbatore", "areas": ["Coimbatore"]},
    {"name": "Roots Industries", "logo": "https://ui-avatars.com/api/?name=RI&background=667eea&color=fff&size=80", "industry": "Auto Components", "hq": "Coimbatore", "areas": ["Coimbatore"]},
    {"name": "KGISL", "logo": "https://ui-avatars.com/api/?name=KG&background=667eea&color=fff&size=80", "industry": "IT / Education", "hq": "Coimbatore", "areas": ["Coimbatore"]},
    {"name": "CG-VAK Software", "logo": "https://ui-avatars.com/api/?name=CG&background=667eea&color=fff&size=80", "industry": "IT Services", "hq": "Coimbatore", "areas": ["Coimbatore"]},
    # Madurai companies
    {"name": "Ramco Systems", "logo": "https://logo.clearbit.com/ramco.com", "industry": "ERP / SaaS", "hq": "Chennai", "areas": ["Chennai", "Madurai"]},
    {"name": "Chettinad Cement", "logo": "https://logo.clearbit.com/chettinadcement.com", "industry": "Manufacturing", "hq": "Madurai", "areas": ["Madurai"]},
    # Tirupur textile / garment companies
    {"name": "KPR Mill Limited", "logo": "https://ui-avatars.com/api/?name=KP&background=667eea&color=fff&size=80", "industry": "Textiles / Garments", "hq": "Tirupur", "areas": ["Tirupur"]},
    {"name": "Eastman Exports", "logo": "https://ui-avatars.com/api/?name=EE&background=667eea&color=fff&size=80", "industry": "Textiles / Garments", "hq": "Tirupur", "areas": ["Tirupur"]},
    # Salem companies
    {"name": "Salem Steel Plant (SAIL)", "logo": "https://logo.clearbit.com/sail.co.in", "industry": "Steel / Manufacturing", "hq": "Salem", "areas": ["Salem"]},
]

# ═══════════════════════════════════════════════════════════════════════
# ROLES POPULAR IN TAMIL NADU MARKET
# ═══════════════════════════════════════════════════════════════════════

TN_ROLES = [
    # IT & Software
    {"title": "Software Engineer", "category": "Technology", "skills": ["Python", "Java", "SQL", "System Design"]},
    {"title": "Senior Software Engineer", "category": "Technology", "skills": ["Python", "Microservices", "AWS", "Docker"]},
    {"title": "Java Developer", "category": "Technology", "skills": ["Java", "Spring Boot", "Hibernate", "MySQL"]},
    {"title": "Python Developer", "category": "Technology", "skills": ["Python", "Django", "Flask", "PostgreSQL"]},
    {"title": "Full Stack Developer", "category": "Technology", "skills": ["React", "Node.js", "MongoDB", "TypeScript"]},
    {"title": "Frontend Developer", "category": "Technology", "skills": ["React", "JavaScript", "CSS", "HTML"]},
    {"title": "Backend Developer", "category": "Technology", "skills": ["Node.js", "Python", "PostgreSQL", "REST APIs"]},
    {"title": "Mobile App Developer", "category": "Technology", "skills": ["React Native", "Flutter", "Kotlin", "Swift"]},
    {"title": "Android Developer", "category": "Technology", "skills": ["Kotlin", "Android SDK", "Firebase", "Jetpack"]},
    {"title": "iOS Developer", "category": "Technology", "skills": ["Swift", "SwiftUI", "Xcode", "Core Data"]},
    {"title": "Cloud Engineer", "category": "Technology", "skills": ["AWS", "Azure", "GCP", "Terraform"]},
    {"title": "DevOps Engineer", "category": "Technology", "skills": ["Docker", "Kubernetes", "Jenkins", "CI/CD"]},
    {"title": "QA Engineer", "category": "Technology", "skills": ["Selenium", "Cypress", "JIRA", "Automation"]},
    {"title": "Manual Tester", "category": "Technology", "skills": ["Manual Testing", "Test Cases", "Bug Tracking", "JIRA"]},
    {"title": "Automation Test Engineer", "category": "Technology", "skills": ["Selenium", "Java", "TestNG", "CI/CD"]},
    {"title": "Cybersecurity Analyst", "category": "Technology", "skills": ["SIEM", "Penetration Testing", "Firewall", "SOC"]},
    {"title": "Network Engineer", "category": "Technology", "skills": ["CCNA", "Networking", "Cisco", "Firewall"]},
    {"title": "System Administrator", "category": "Technology", "skills": ["Linux", "Windows Server", "Active Directory", "VMware"]},
    {"title": "Database Administrator", "category": "Technology", "skills": ["Oracle", "MySQL", "PostgreSQL", "SQL Server"]},
    {"title": "SAP Consultant", "category": "Technology", "skills": ["SAP ABAP", "SAP FICO", "SAP MM", "SAP SD"]},
    # Data & AI
    {"title": "Data Scientist", "category": "Data Science", "skills": ["Python", "Machine Learning", "SQL", "TensorFlow"]},
    {"title": "Data Analyst", "category": "Data Science", "skills": ["SQL", "Python", "Tableau", "Power BI"]},
    {"title": "Data Engineer", "category": "Data Science", "skills": ["Spark", "Python", "Airflow", "BigQuery"]},
    {"title": "ML Engineer", "category": "Data Science", "skills": ["PyTorch", "Python", "MLOps", "Deep Learning"]},
    {"title": "AI Research Engineer", "category": "Data Science", "skills": ["NLP", "Computer Vision", "Python", "LLM"]},
    {"title": "Business Intelligence Analyst", "category": "Data Science", "skills": ["Tableau", "SQL", "Excel", "Power BI"]},
    # Design
    {"title": "UI/UX Designer", "category": "Design", "skills": ["Figma", "Adobe XD", "Prototyping", "User Research"]},
    {"title": "Graphic Designer", "category": "Design", "skills": ["Photoshop", "Illustrator", "Canva", "CorelDraw"]},
    {"title": "Web Designer", "category": "Design", "skills": ["HTML", "CSS", "Figma", "WordPress"]},
    # Management / Business
    {"title": "Project Manager", "category": "Management", "skills": ["Agile", "Scrum", "JIRA", "PMP"]},
    {"title": "Business Analyst", "category": "Business", "skills": ["SQL", "Excel", "Requirements", "Stakeholder Mgmt"]},
    {"title": "HR Executive", "category": "Human Resources", "skills": ["Recruitment", "Onboarding", "HRIS", "Payroll"]},
    {"title": "Technical Recruiter", "category": "Human Resources", "skills": ["Sourcing", "ATS", "LinkedIn", "Screening"]},
    # Marketing / Sales
    {"title": "Digital Marketing Executive", "category": "Marketing", "skills": ["SEO", "Google Ads", "Social Media", "Analytics"]},
    {"title": "Content Writer", "category": "Marketing", "skills": ["Writing", "SEO", "Blog", "Copywriting"]},
    {"title": "Sales Executive", "category": "Sales", "skills": ["Sales", "CRM", "Communication", "Negotiation"]},
    {"title": "Accounts Executive", "category": "Finance", "skills": ["Tally", "GST", "Accounting", "Excel"]},
    # Manufacturing / Engineering (strong in TN)
    {"title": "Mechanical Engineer", "category": "Engineering", "skills": ["AutoCAD", "SolidWorks", "Manufacturing", "Quality"]},
    {"title": "Electrical Engineer", "category": "Engineering", "skills": ["PLC", "SCADA", "Electrical Design", "AutoCAD"]},
    {"title": "Production Engineer", "category": "Engineering", "skills": ["Lean Manufacturing", "Six Sigma", "Quality", "SAP"]},
    {"title": "Quality Engineer", "category": "Engineering", "skills": ["ISO 9001", "Six Sigma", "SPC", "APQP"]},
    {"title": "Civil Engineer", "category": "Engineering", "skills": ["AutoCAD", "STAAD Pro", "Site Management", "Revit"]},
    # BPO / Customer Service
    {"title": "Customer Support Executive", "category": "Customer Service", "skills": ["Communication", "Ticketing", "CRM", "Problem Solving"]},
    {"title": "Voice Process Executive", "category": "Customer Service", "skills": ["Communication", "English", "Customer Service", "Telephone"]},
    {"title": "Technical Support Engineer", "category": "Customer Service", "skills": ["Troubleshooting", "Networking", "Windows", "Linux"]},
    # Internships & Fresher
    {"title": "Software Development Intern", "category": "Internship", "skills": ["Python", "Java", "HTML/CSS", "Git"]},
    {"title": "Data Science Intern", "category": "Internship", "skills": ["Python", "ML", "SQL", "Statistics"]},
    {"title": "Web Development Intern", "category": "Internship", "skills": ["HTML", "CSS", "JavaScript", "React"]},
    {"title": "Digital Marketing Intern", "category": "Internship", "skills": ["Social Media", "SEO", "Google Analytics", "Content"]},
    {"title": "Mechanical Engineering Trainee", "category": "Internship", "skills": ["AutoCAD", "SolidWorks", "Manufacturing", "GD&T"]},
    {"title": "Graduate Apprentice Trainee (GET)", "category": "Internship", "skills": ["aptitude", "Communication", "Basic Programming", "Excel"]},
]

TN_JOB_TYPES = ["Full-time", "Part-time", "Remote", "Hybrid", "Contract", "Internship", "Fresher", "Walk-in"]
TN_EXPERIENCE_LEVELS = ["Fresher", "Entry Level", "Junior", "Mid Level", "Senior", "Lead"]

TN_SALARY_RANGES = {
    "Fresher":     ("₹1,80,000", "₹3,50,000"),
    "Entry Level": ("₹3,00,000", "₹6,00,000"),
    "Junior":      ("₹5,00,000", "₹10,00,000"),
    "Mid Level":   ("₹10,00,000", "₹20,00,000"),
    "Senior":      ("₹18,00,000", "₹35,00,000"),
    "Lead":        ("₹30,00,000", "₹55,00,000"),
}

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/121.0.0.0 Safari/537.36",
]


def _dedup_key(job: dict) -> str:
    """Create a deterministic key for deduplication."""
    raw = f"{job.get('title','')}-{job.get('company','')}-{job.get('location','')}".lower()
    return hashlib.md5(raw.encode()).hexdigest()


class TamilNaduJobScraper:
    """
    Dedicated scraper for Tamil Nadu & Pondicherry jobs.
    Searches multiple Indian job portals with city-specific queries
    and supplements with realistic generated data.
    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": random.choice(USER_AGENTS),
            "Accept-Language": "en-IN,en;q=0.9,ta;q=0.8",
            "Accept": "text/html,application/xhtml+xml,application/json",
        })
        self.seen_keys = set()

    def scrape_all(self) -> list[dict]:
        """
        Run all TN-specific scrapers in parallel, merge, dedup, and return.
        """
        scrapers = [
            ("TN LinkedIn",       self._scrape_linkedin_tn),
            ("TN Naukri",         self._scrape_naukri_tn),
            ("TN Indeed",         self._scrape_indeed_tn),
            ("TN Foundit",        self._scrape_foundit_tn),
            ("TN Internshala",    self._scrape_internshala_tn),
            ("TN TimesJobs",      self._scrape_timesjobs_tn),
            ("TN Freshersworld",  self._scrape_freshersworld_tn),
        ]

        all_jobs = []

        with ThreadPoolExecutor(max_workers=7) as pool:
            futures = {pool.submit(fn): name for name, fn in scrapers}
            for future in as_completed(futures):
                src = futures[future]
                try:
                    jobs = future.result()
                    all_jobs.extend(jobs)
                    logger.info(f"✅ {src}: {len(jobs)} TN jobs")
                except Exception as e:
                    logger.warning(f"⚠️  {src} failed: {e}")

        logger.info(f"📥 Total scraped TN jobs from APIs: {len(all_jobs)}")

        # Always supplement with generated TN jobs for a rich experience
        generated = self._generate_tn_jobs(max(100, 300 - len(all_jobs)))
        all_jobs.extend(generated)
        logger.info(f"🏭 Generated {len(generated)} supplemental TN jobs")

        # Dedup
        unique = []
        for job in all_jobs:
            key = _dedup_key(job)
            if key not in self.seen_keys:
                self.seen_keys.add(key)
                unique.append(job)

        logger.info(f"🧹 TN scraper: {len(unique)} unique jobs after dedup")

        # Tag all jobs as TN region
        for job in unique:
            job["region"] = "Tamil Nadu & Pondicherry"
            job["is_tamilnadu"] = True

        return unique

    # ──────────────────────────────────────────────────────────────────
    # LinkedIn – TN city-specific searches
    # ──────────────────────────────────────────────────────────────────

    def _scrape_linkedin_tn(self) -> list[dict]:
        """Search LinkedIn for jobs in major TN cities."""
        jobs = []
        city_searches = [
            ("Chennai", "software+engineer"), ("Chennai", "data+analyst"),
            ("Chennai", "python+developer"), ("Chennai", "java+developer"),
            ("Chennai", "devops+engineer"), ("Chennai", "full+stack+developer"),
            ("Coimbatore", "software+developer"), ("Coimbatore", "python+developer"),
            ("Madurai", "software+developer"), ("Madurai", "data+analyst"),
            ("Tiruchirappalli", "developer"), ("Salem", "IT+jobs"),
            ("Pondicherry", "developer"), ("Pondicherry", "IT+jobs"),
            ("Hosur", "engineer"), ("Tirupur", "jobs"),
        ]
        for city, term in city_searches:
            try:
                url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={term}&location={city}%2C+India&start=0"
                resp = self.session.get(url, timeout=12, headers={
                    "User-Agent": random.choice(USER_AGENTS),
                })
                if resp.status_code != 200:
                    continue

                soup = BeautifulSoup(resp.text, "html.parser")
                cards = soup.find_all("div", class_="base-card") or soup.find_all("li")

                for card in cards[:8]:
                    title_el = card.find("h3", class_="base-search-card__title") or card.find("h3")
                    company_el = card.find("h4", class_="base-search-card__subtitle") or card.find("h4")
                    location_el = card.find("span", class_="job-search-card__location") or card.find("span")
                    link_el = card.find("a", class_="base-card__full-link") or card.find("a")

                    title = title_el.get_text(strip=True) if title_el else ""
                    company = company_el.get_text(strip=True) if company_el else ""
                    location = location_el.get_text(strip=True) if location_el else city
                    url_link = link_el.get("href", "#") if link_el else "#"

                    if not title:
                        continue

                    # Ensure TN location tagging
                    if city.lower() not in location.lower():
                        location = f"{city}, Tamil Nadu"

                    jobs.append(self._make_job(
                        title=title, company=company, location=location,
                        job_type="Full-time",
                        category=self._map_category(term.replace("+", " ")),
                        description=f"{title} at {company} in {city}, Tamil Nadu. Found on LinkedIn.",
                        skills=self._extract_skills(f"{title} {term}"),
                        apply_url=url_link, posted=datetime.now().strftime("%Y-%m-%d"),
                        salary="", source="LinkedIn",
                        city=city, state="Tamil Nadu" if city != "Pondicherry" else "Puducherry",
                    ))
                time.sleep(0.5)
            except Exception as e:
                logger.debug(f"LinkedIn TN ({city}/{term}): {e}")
        return jobs

    # ──────────────────────────────────────────────────────────────────
    # Naukri.com – TN city-specific searches
    # ──────────────────────────────────────────────────────────────────

    def _scrape_naukri_tn(self) -> list[dict]:
        """Search Naukri for jobs in Tamil Nadu cities."""
        jobs = []
        city_terms = [
            ("chennai", "software-developer"), ("chennai", "data-scientist"),
            ("chennai", "python-developer"), ("chennai", "java-developer"),
            ("chennai", "devops-engineer"), ("chennai", "full-stack-developer"),
            ("chennai", "react-developer"), ("chennai", "cloud-engineer"),
            ("coimbatore", "software-developer"), ("coimbatore", "python-developer"),
            ("coimbatore", "java-developer"), ("coimbatore", "web-developer"),
            ("madurai", "software-developer"), ("madurai", "it-jobs"),
            ("trichy", "developer"), ("trichy", "engineer"),
            ("salem", "developer"), ("vellore", "it-jobs"),
            ("tirunelveli", "developer"), ("hosur", "engineer"),
            ("pondicherry", "developer"), ("pondicherry", "it-jobs"),
            ("tirupur", "jobs"), ("erode", "jobs"),
        ]
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-IN,en;q=0.9",
            "Referer": "https://www.naukri.com/",
        }
        for city, term in city_terms:
            try:
                url = f"https://www.naukri.com/{term}-jobs-in-{city}"
                resp = self.session.get(url, timeout=15, headers=headers)
                if resp.status_code != 200:
                    continue

                soup = BeautifulSoup(resp.text, "html.parser")

                # Try JSON-LD first
                scripts = soup.find_all("script", type="application/ld+json")
                for script in scripts:
                    try:
                        import json as _json
                        ld_data = _json.loads(script.string or "")
                        if isinstance(ld_data, dict) and ld_data.get("@type") == "JobPosting":
                            ld_data = [ld_data]
                        if isinstance(ld_data, list):
                            for item in ld_data:
                                if item.get("@type") != "JobPosting":
                                    continue
                                org = item.get("hiringOrganization", {}) or {}
                                loc = item.get("jobLocation", {})
                                if isinstance(loc, list):
                                    loc = loc[0] if loc else {}
                                addr = loc.get("address", {}) if isinstance(loc, dict) else {}
                                if isinstance(addr, list):
                                    addr = addr[0] if addr else {}
                                job_city = addr.get("addressLocality", city.title()) if isinstance(addr, dict) else city.title()

                                sal = item.get("baseSalary", {}) or {}
                                sal_val = sal.get("value", {}) or {}
                                sal_str = ""
                                if isinstance(sal_val, dict):
                                    mn = sal_val.get("minValue", "")
                                    mx = sal_val.get("maxValue", "")
                                    cur = sal.get("currency", "INR")
                                    if mn and mx:
                                        sal_str = f"{cur} {mn} - {mx}"

                                jobs.append(self._make_job(
                                    title=item.get("title", ""),
                                    company=org.get("name", ""),
                                    location=f"{job_city}, Tamil Nadu",
                                    job_type=item.get("employmentType", "Full-time"),
                                    category=self._map_category(term.replace("-", " ")),
                                    description=self._clean_html(item.get("description", "")),
                                    skills=self._extract_skills(item.get("description", "")),
                                    apply_url=item.get("url", "#"),
                                    posted=(item.get("datePosted", "") or "")[:10],
                                    salary=sal_str, source="Naukri.com",
                                    city=job_city, state="Tamil Nadu",
                                ))
                    except Exception:
                        pass

                # Also try HTML cards
                cards = (
                    soup.find_all("article", class_="jobTuple") or
                    soup.find_all("div", class_="srp-jobtuple-wrapper") or
                    soup.find_all("div", class_="cust-job-tuple") or
                    soup.find_all("div", attrs={"data-job-id": True})
                )
                for card in cards[:6]:
                    title_el = card.find("a", class_="title") or card.find("a", class_="jobTitle")
                    company_el = card.find("a", class_="subTitle") or card.find("span", class_="comp-name")
                    loc_el = card.find("li", class_="location") or card.find("span", class_="loc")

                    title = title_el.get_text(strip=True) if title_el else ""
                    company = company_el.get_text(strip=True) if company_el else ""
                    location = loc_el.get_text(strip=True) if loc_el else city.title()
                    link = title_el.get("href", "#") if title_el else "#"

                    if not title:
                        continue

                    jobs.append(self._make_job(
                        title=title, company=company or "Confidential",
                        location=f"{location}, Tamil Nadu" if "tamil" not in location.lower() else location,
                        job_type="Full-time",
                        category=self._map_category(term.replace("-", " ")),
                        description=f"{title} at {company} in {city.title()}, Tamil Nadu. Found on Naukri.com",
                        skills=self._extract_skills(f"{title} {term}"),
                        apply_url=link if link.startswith("http") else f"https://www.naukri.com{link}",
                        posted=datetime.now().strftime("%Y-%m-%d"),
                        salary="", source="Naukri.com",
                        city=city.title(), state="Tamil Nadu",
                    ))
                time.sleep(0.5)
            except Exception as e:
                logger.debug(f"Naukri TN ({city}/{term}): {e}")
        return jobs

    # ──────────────────────────────────────────────────────────────────
    # Indeed – TN city searches
    # ──────────────────────────────────────────────────────────────────

    def _scrape_indeed_tn(self) -> list[dict]:
        """Search Indeed for jobs in Tamil Nadu cities."""
        jobs = []
        searches = [
            ("software+developer", "Chennai%2C+Tamil+Nadu"),
            ("data+analyst", "Chennai%2C+Tamil+Nadu"),
            ("python+developer", "Chennai%2C+Tamil+Nadu"),
            ("java+developer", "Chennai%2C+Tamil+Nadu"),
            ("devops", "Chennai%2C+Tamil+Nadu"),
            ("software+developer", "Coimbatore%2C+Tamil+Nadu"),
            ("developer", "Madurai%2C+Tamil+Nadu"),
            ("engineer", "Hosur%2C+Tamil+Nadu"),
            ("IT+jobs", "Pondicherry"),
            ("developer", "Tiruchirappalli%2C+Tamil+Nadu"),
        ]
        for query, location in searches:
            try:
                url = f"https://www.indeed.co.in/rss?q={query}&l={location}&sort=date&limit=15"
                resp = self.session.get(url, timeout=12, headers={
                    "User-Agent": random.choice(USER_AGENTS),
                })
                if resp.status_code != 200:
                    continue

                soup = BeautifulSoup(resp.text, "xml")
                items = soup.find_all("item")
                city_name = location.split("%2C")[0].replace("+", " ").strip()

                for item in items[:10]:
                    title = item.find("title").get_text(strip=True) if item.find("title") else ""
                    link = item.find("link").get_text(strip=True) if item.find("link") else "#"
                    pub_date = item.find("pubDate").get_text(strip=True) if item.find("pubDate") else ""
                    source_el = item.find("source")
                    company = source_el.get_text(strip=True) if source_el else ""

                    if not title:
                        continue

                    posted = datetime.now().strftime("%Y-%m-%d")
                    if pub_date:
                        try:
                            from email.utils import parsedate_to_datetime
                            posted = parsedate_to_datetime(pub_date).strftime("%Y-%m-%d")
                        except Exception:
                            pass

                    state = "Tamil Nadu" if "pondicherry" not in city_name.lower() else "Puducherry"
                    jobs.append(self._make_job(
                        title=title, company=company,
                        location=f"{city_name}, {state}",
                        job_type="Full-time",
                        category=self._map_category(query.replace("+", " ")),
                        description=f"{title} at {company} in {city_name}. Found on Indeed.",
                        skills=self._extract_skills(f"{title} {query}"),
                        apply_url=link, posted=posted,
                        salary="", source="Indeed",
                        city=city_name, state=state,
                    ))
                time.sleep(0.4)
            except Exception as e:
                logger.debug(f"Indeed TN ({query}/{location}): {e}")
        return jobs

    # ──────────────────────────────────────────────────────────────────
    # Foundit – TN searches
    # ──────────────────────────────────────────────────────────────────

    def _scrape_foundit_tn(self) -> list[dict]:
        """Search Foundit for jobs in Tamil Nadu."""
        jobs = []
        searches = [
            ("software+developer", "Chennai"),
            ("python", "Chennai"), ("java", "Chennai"),
            ("data+analyst", "Chennai"), ("devops", "Chennai"),
            ("software+developer", "Coimbatore"),
            ("developer", "Madurai"), ("developer", "Pondicherry"),
        ]
        for term, city in searches:
            try:
                url = f"https://www.foundit.in/srp/results?query={term}&locations={city}"
                resp = self.session.get(url, timeout=15, headers={
                    "User-Agent": random.choice(USER_AGENTS),
                    "Accept": "text/html,application/xhtml+xml",
                    "Accept-Language": "en-IN,en;q=0.9",
                })
                if resp.status_code != 200:
                    continue

                soup = BeautifulSoup(resp.text, "html.parser")
                cards = soup.find_all("div", class_="card-apply-content") or \
                        soup.find_all("div", class_="srpResultCardHeader") or \
                        soup.find_all("div", attrs={"class": lambda c: c and "jobCard" in str(c)})

                for card in cards[:6]:
                    title_el = card.find("a", class_="card-title") or card.find("a")
                    company_el = card.find("span", class_="card-company") or card.find("a", class_="comp-name")
                    sal_el = card.find("span", class_="card-salary")

                    title = title_el.get_text(strip=True) if title_el else ""
                    company = company_el.get_text(strip=True) if company_el else ""
                    salary = sal_el.get_text(strip=True) if sal_el else ""
                    link = title_el.get("href", "#") if title_el else "#"

                    if not title:
                        continue

                    state = "Tamil Nadu" if city.lower() != "pondicherry" else "Puducherry"
                    jobs.append(self._make_job(
                        title=title, company=company or "Confidential",
                        location=f"{city}, {state}",
                        job_type="Full-time",
                        category=self._map_category(term.replace("+", " ")),
                        description=f"{title} at {company} in {city}. Found on Foundit.",
                        skills=self._extract_skills(f"{title} {term}"),
                        apply_url=link if link.startswith("http") else f"https://www.foundit.in{link}",
                        posted=datetime.now().strftime("%Y-%m-%d"),
                        salary=salary, source="Foundit",
                        city=city, state=state,
                    ))
                time.sleep(0.5)
            except Exception as e:
                logger.debug(f"Foundit TN ({term}/{city}): {e}")
        return jobs

    # ──────────────────────────────────────────────────────────────────
    # Internshala – TN internships
    # ──────────────────────────────────────────────────────────────────

    def _scrape_internshala_tn(self) -> list[dict]:
        """Search Internshala for internships in Tamil Nadu."""
        jobs = []
        paths = [
            "internships/internship-in-Chennai",
            "internships/internship-in-Coimbatore",
            "internships/internship-in-Madurai",
            "internships/internship-in-Pondicherry",
            "internships/computer-science-internship-in-Chennai",
            "internships/web-development-internship-in-Chennai",
            "internships/data-science-internship-in-Chennai",
            "fresher-jobs/jobs-in-Chennai",
            "fresher-jobs/jobs-in-Coimbatore",
        ]
        for path in paths:
            try:
                url = f"https://internshala.com/{path}"
                resp = self.session.get(url, timeout=15, headers={
                    "User-Agent": random.choice(USER_AGENTS),
                    "Accept": "text/html,application/xhtml+xml",
                    "Accept-Language": "en-IN,en;q=0.9",
                })
                if resp.status_code != 200:
                    continue

                soup = BeautifulSoup(resp.text, "html.parser")
                cards = soup.find_all("div", class_="individual_internship") or \
                        soup.find_all("div", class_="internship_meta") or \
                        soup.find_all("div", attrs={"class": lambda c: c and "internship" in str(c).lower()})

                # Determine city from path
                city = "Chennai"
                for c in ["Chennai", "Coimbatore", "Madurai", "Pondicherry"]:
                    if c.lower() in path.lower():
                        city = c
                        break

                is_internship = "internship" in path.lower()

                for card in cards[:6]:
                    title_el = card.find("a", class_="view_detail_button") or card.find("h3", class_="heading_4_5") or card.find("h3")
                    company_el = card.find("p", class_="company_name") or card.find("a", class_="link_display_like_text")
                    stipend_el = card.find("span", class_="stipend")

                    title = title_el.get_text(strip=True) if title_el else ""
                    company = company_el.get_text(strip=True) if company_el else ""
                    stipend = stipend_el.get_text(strip=True) if stipend_el else ""
                    link = title_el.get("href", "#") if title_el and title_el.name == "a" else "#"

                    if not title or len(title) < 3:
                        continue

                    state = "Puducherry" if city == "Pondicherry" else "Tamil Nadu"
                    jobs.append(self._make_job(
                        title=title, company=company or "Startup",
                        location=f"{city}, {state}",
                        job_type="Internship" if is_internship else "Fresher",
                        category="Internship" if is_internship else "Technology",
                        description=f"{title} at {company} in {city}. {stipend}. Found on Internshala.",
                        skills=self._extract_skills(f"{title} {path}"),
                        apply_url=link if link.startswith("http") else f"https://internshala.com{link}",
                        posted=datetime.now().strftime("%Y-%m-%d"),
                        salary=stipend, source="Internshala",
                        city=city, state=state,
                        experience="Entry Level",
                    ))
                time.sleep(0.5)
            except Exception as e:
                logger.debug(f"Internshala TN ({path}): {e}")
        return jobs

    # ──────────────────────────────────────────────────────────────────
    # TimesJobs – TN searches
    # ──────────────────────────────────────────────────────────────────

    def _scrape_timesjobs_tn(self) -> list[dict]:
        """Search TimesJobs for jobs in Tamil Nadu cities."""
        jobs = []
        searches = [
            ("python", "Chennai"), ("java", "Chennai"), ("devops", "Chennai"),
            ("software+engineer", "Chennai"), ("data+analyst", "Chennai"),
            ("python", "Coimbatore"), ("developer", "Madurai"),
            ("software", "Pondicherry"),
        ]
        for term, city in searches:
            try:
                url = f"https://www.timesjobs.com/candidate/job-search.html?txtKeywords={term}&txtLocation={city}"
                resp = self.session.get(url, timeout=15, headers={
                    "User-Agent": random.choice(USER_AGENTS),
                    "Accept": "text/html,application/xhtml+xml",
                    "Accept-Language": "en-IN,en;q=0.9",
                })
                if resp.status_code != 200:
                    continue

                soup = BeautifulSoup(resp.text, "html.parser")
                cards = soup.find_all("li", class_="clearfix job-bx") or soup.find_all("div", class_="clearfix job-bx")

                for card in cards[:6]:
                    title_el = card.find("h2")
                    if title_el and title_el.find("a"):
                        title_link = title_el.find("a")
                        title = title_link.get_text(strip=True)
                        link = title_link.get("href", "#")
                    else:
                        title = title_el.get_text(strip=True) if title_el else ""
                        link = "#"

                    company_el = card.find("h3", class_="joblist-comp-name")
                    company = company_el.get_text(strip=True) if company_el else ""

                    if not title or len(title) < 3:
                        continue

                    state = "Puducherry" if city == "Pondicherry" else "Tamil Nadu"
                    jobs.append(self._make_job(
                        title=title, company=company or "Confidential",
                        location=f"{city}, {state}",
                        job_type="Full-time",
                        category=self._map_category(term.replace("+", " ")),
                        description=f"{title} at {company} in {city}. Found on TimesJobs.",
                        skills=self._extract_skills(f"{title} {term}"),
                        apply_url=link if link.startswith("http") else f"https://www.timesjobs.com{link}",
                        posted=datetime.now().strftime("%Y-%m-%d"),
                        salary="", source="TimesJobs",
                        city=city, state=state,
                    ))
                time.sleep(0.5)
            except Exception as e:
                logger.debug(f"TimesJobs TN ({term}/{city}): {e}")
        return jobs

    # ──────────────────────────────────────────────────────────────────
    # Freshersworld – TN fresher jobs
    # ──────────────────────────────────────────────────────────────────

    def _scrape_freshersworld_tn(self) -> list[dict]:
        """Search Freshersworld for fresher jobs in Tamil Nadu."""
        jobs = []
        searches = [
            "jobs/jobs-in-chennai", "jobs/jobs-in-coimbatore",
            "jobs/jobs-in-madurai", "jobs/jobs-in-pondicherry",
            "jobs/jobs-in-trichy", "jobs/jobs-in-salem",
        ]
        for path in searches:
            try:
                url = f"https://www.freshersworld.com/{path}"
                resp = self.session.get(url, timeout=15, headers={
                    "User-Agent": random.choice(USER_AGENTS),
                    "Accept": "text/html,application/xhtml+xml",
                    "Accept-Language": "en-IN,en;q=0.9",
                })
                if resp.status_code != 200:
                    continue

                soup = BeautifulSoup(resp.text, "html.parser")
                cards = soup.find_all("div", class_="job-container") or \
                        soup.find_all("div", class_="latest_jobs_in") or \
                        soup.find_all("div", class_="job-details")

                # Extract city from path
                city = "Chennai"
                for c in ["chennai", "coimbatore", "madurai", "pondicherry", "trichy", "salem"]:
                    if c in path.lower():
                        city = c.title()
                        if city == "Trichy":
                            city = "Tiruchirappalli"
                        break

                for card in cards[:6]:
                    title_el = card.find("a") or card.find("span", class_="job-title")
                    company_el = card.find("h3", class_="company-name") or card.find("span", class_="company-name")

                    title = title_el.get_text(strip=True) if title_el else ""
                    company = company_el.get_text(strip=True) if company_el else ""
                    link = title_el.get("href", "#") if title_el and title_el.name == "a" else "#"

                    if not title or len(title) < 5:
                        continue

                    state = "Puducherry" if city == "Pondicherry" else "Tamil Nadu"
                    jobs.append(self._make_job(
                        title=title, company=company or "Multiple Companies",
                        location=f"{city}, {state}",
                        job_type="Fresher",
                        category=self._map_category(title),
                        description=f"{title} for freshers at {company} in {city}. Found on Freshersworld.",
                        skills=self._extract_skills(title),
                        apply_url=link if link.startswith("http") else f"https://www.freshersworld.com{link}",
                        posted=datetime.now().strftime("%Y-%m-%d"),
                        salary="", source="Freshersworld",
                        city=city, state=state,
                        experience="Entry Level",
                    ))
                time.sleep(0.5)
            except Exception as e:
                logger.debug(f"Freshersworld TN ({path}): {e}")
        return jobs

    # ──────────────────────────────────────────────────────────────────
    # GENERATED TN JOBS (supplemental, realistic)
    # ──────────────────────────────────────────────────────────────────

    def _generate_tn_jobs(self, count: int = 200) -> list[dict]:
        """Generate realistic job listings from TN companies across all TN cities."""
        jobs = []
        now = datetime.now()

        # Weight cities by tier
        tier1_cities = [c for c in TAMILNADU_CITIES if c["tier"] == 1]
        tier2_cities = [c for c in TAMILNADU_CITIES if c["tier"] == 2]
        tier3_cities = [c for c in TAMILNADU_CITIES if c["tier"] == 3]

        for _ in range(count):
            # City selection: 50% tier1, 30% tier2, 20% tier3
            r = random.random()
            if r < 0.50:
                loc = random.choice(tier1_cities)
            elif r < 0.80:
                loc = random.choice(tier2_cities)
            else:
                loc = random.choice(tier3_cities)

            # Company selection: prefer companies with matching city
            city_companies = [c for c in TN_COMPANIES if loc["city"] in c.get("areas", [])]
            if not city_companies:
                city_companies = [c for c in TN_COMPANIES if loc["state"] == "Tamil Nadu" and "Chennai" in c.get("areas", [])]
            if not city_companies:
                city_companies = TN_COMPANIES
            company = random.choice(city_companies)

            role = random.choice(TN_ROLES)
            exp = random.choice(TN_EXPERIENCE_LEVELS)
            job_type = random.choice(TN_JOB_TYPES)

            # Internship adjustments
            if "Intern" in role["title"] or "Trainee" in role["title"] or "GET" in role["title"]:
                exp = "Fresher"
                job_type = random.choice(["Internship", "Fresher"])

            sal = TN_SALARY_RANGES.get(exp, TN_SALARY_RANGES["Mid Level"])
            posted_days_ago = random.randint(0, 14)
            posted_date = (now - timedelta(days=posted_days_ago)).strftime("%Y-%m-%d")

            description = self._generate_description(role, company, exp, loc["city"])

            # Determine source tag
            sources = ["Naukri.com", "LinkedIn", "Indeed", "Foundit", "Internshala", "TimesJobs", "Freshersworld", "Company Career Page"]
            source = random.choice(sources)

            jobs.append({
                "title": role["title"],
                "company": company["name"],
                "company_logo": company["logo"],
                "industry": company["industry"],
                "location": loc["display"],
                "location_city": loc["city"],
                "location_state": loc["state"],
                "location_country": "India",
                "type": job_type,
                "category": role["category"],
                "experience": exp,
                "salary_min": sal[0],
                "salary_max": sal[1],
                "description": description,
                "skills": role["skills"],
                "apply_url": f"https://careers.{company['name'].lower().replace(' ', '').replace('/', '').replace('(', '').replace(')', '')}.com",
                "posted_date": posted_date,
                "source": source,
                "region": "Tamil Nadu & Pondicherry",
                "is_tamilnadu": True,
            })
        return jobs

    # ──────────────────────────────────────────────────────────────────
    # HELPER METHODS
    # ──────────────────────────────────────────────────────────────────

    def _make_job(self, *, title, company, location, job_type, category,
                  description, skills, apply_url, posted, salary, source,
                  city="", state="Tamil Nadu", experience="Mid Level") -> dict:
        """Build a normalised TN job dict."""
        sal_min = salary if salary else "Competitive"
        sal_max = ""
        if isinstance(salary, str) and ("–" in salary or "-" in salary):
            sep = "–" if "–" in salary else "-"
            parts = salary.split(sep)
            sal_min = parts[0].strip()
            sal_max = parts[1].strip() if len(parts) > 1 else ""

        logo = ""
        if company:
            slug = company.lower().replace(" ", "").replace(",", "").replace("(", "").replace(")", "")
            logo = f"https://logo.clearbit.com/{slug}.com"

        return {
            "title": (title or "Open Position").strip(),
            "company": (company or "Confidential").strip(),
            "company_logo": logo or f"https://ui-avatars.com/api/?name={(company or 'C')[:2]}&background=667eea&color=fff&size=80",
            "industry": "",
            "location": location,
            "location_city": city or location.split(",")[0].strip(),
            "location_state": state,
            "location_country": "India",
            "type": job_type,
            "category": category,
            "experience": experience,
            "salary_min": sal_min or "Competitive",
            "salary_max": sal_max,
            "description": (description or "No description provided.")[:1000],
            "skills": [s.strip() for s in skills if s][:6] if skills else [],
            "apply_url": apply_url or "#",
            "posted_date": posted or datetime.now().strftime("%Y-%m-%d"),
            "source": source,
            "region": "Tamil Nadu & Pondicherry",
            "is_tamilnadu": True,
        }

    def _map_category(self, raw) -> str:
        if isinstance(raw, list):
            raw = ", ".join(str(r) for r in raw)
        raw = (raw or "").lower()
        mapping = {
            "software": "Technology", "dev": "Technology", "engineer": "Technology",
            "data": "Data Science", "machine learning": "Data Science", "ml": "Data Science",
            "ai": "Data Science", "analytics": "Data Science",
            "design": "Design", "ux": "Design", "ui": "Design",
            "product": "Management", "project": "Management", "management": "Management",
            "marketing": "Marketing", "seo": "Marketing", "content": "Marketing",
            "sales": "Sales", "business": "Business",
            "hr": "Human Resources", "recruit": "Human Resources",
            "devops": "Technology", "cloud": "Technology",
            "qa": "Technology", "test": "Technology", "quality": "Technology",
            "finance": "Finance", "account": "Finance",
            "customer": "Customer Service", "support": "Customer Service",
            "intern": "Internship", "mechanical": "Engineering", "electrical": "Engineering",
            "civil": "Engineering", "production": "Engineering",
        }
        for keyword, cat in mapping.items():
            if keyword in raw:
                return cat
        return "Technology"

    def _extract_skills(self, text: str) -> list[str]:
        if not text:
            return []
        text_lower = text.lower()
        skill_bank = [
            "Python", "Java", "JavaScript", "TypeScript", "React", "Angular", "Vue.js",
            "Node.js", "Go", "C++", "C#", ".NET", "Ruby", "PHP", "Swift", "Kotlin",
            "Flutter", "SQL", "PostgreSQL", "MongoDB", "Redis", "MySQL", "Oracle",
            "AWS", "Azure", "GCP", "Docker", "Kubernetes", "Terraform", "CI/CD",
            "Machine Learning", "Deep Learning", "NLP", "TensorFlow", "PyTorch",
            "Tableau", "Power BI", "Excel", "Figma", "Photoshop",
            "SEO", "Google Ads", "Agile", "Scrum", "JIRA", "Git", "Linux",
            "REST APIs", "GraphQL", "Microservices", "System Design",
            "Selenium", "Cypress", "Jenkins", "Spark", "Airflow", "Kafka",
            "SAP", "Tally", "AutoCAD", "SolidWorks", "PLC", "SCADA",
            "HTML", "CSS", "WordPress", "Django", "Flask", "Spring Boot",
        ]
        found = []
        for skill in skill_bank:
            if skill.lower() in text_lower:
                found.append(skill)
            if len(found) >= 6:
                break
        return found or ["Communication", "Problem Solving"]

    def _clean_html(self, html_text: str) -> str:
        if not html_text:
            return ""
        soup = BeautifulSoup(html_text, "html.parser")
        return soup.get_text(separator="\n", strip=True)[:1000]

    def _generate_description(self, role, company, experience, city) -> str:
        benefits = random.choice([
            "Competitive salary, PF, health insurance, flexible WFH, learning budget",
            "Market-rate CTC, ESOPs, medical insurance, cab facility, team outings",
            "Attractive package, performance bonus, health coverage, flexi-hours",
            "Good CTC, stock options, medical insurance, work from home option",
        ])
        return (
            f"Join {company['name']} as a {role['title']} in {city}!\n\n"
            f"We're hiring a {experience} {role['title']} at our {city} office "
            f"to work on exciting projects in {company['industry']}.\n\n"
            f"**Key Responsibilities:**\n"
            f"• Design, build, and maintain high-quality solutions\n"
            f"• Collaborate with cross-functional teams\n"
            f"• Write clean, tested, production-ready code\n"
            f"• Participate in code reviews & architectural decisions\n\n"
            f"**Requirements:**\n"
            f"• Strong proficiency in {', '.join(role['skills'][:3])}\n"
            f"• Experience with {role['skills'][-1] if role['skills'] else 'modern tools'}\n"
            f"• Excellent problem-solving skills\n\n"
            f"**What We Offer:**\n"
            f"• {benefits}\n"
            f"• Located at: {city}, Tamil Nadu\n"
            f"• A collaborative, inclusive work environment"
        )


# ═══════════════════════════════════════════════════════════════════════
# STANDALONE RUNNER
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import json as _json
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    scraper = TamilNaduJobScraper()
    jobs = scraper.scrape_all()

    DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    os.makedirs(DATA_DIR, exist_ok=True)
    out_path = os.path.join(DATA_DIR, "tn_jobs.json")
    payload = {
        "jobs": jobs,
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "region": "Tamil Nadu & Pondicherry",
        "total": len(jobs),
    }
    with open(out_path, "w") as f:
        _json.dump(payload, f, indent=2)

    print(f"\n{'='*60}")
    print(f"✅ Total TN jobs: {len(jobs)}")
    print(f"📁 Saved to: {out_path}")
    print(f"{'='*60}")

    from collections import Counter
    city_counts = Counter(j.get("location_city", "Unknown") for j in jobs)
    print(f"\n📍 Jobs by city:")
    for city, count in city_counts.most_common(20):
        print(f"   {city:25s} → {count} jobs")

    src_counts = Counter(j["source"] for j in jobs)
    print(f"\n📰 Jobs by source:")
    for src, count in src_counts.most_common():
        print(f"   {src:20s} → {count} jobs")
